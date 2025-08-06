# Copyright 2024 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Script to run the SpeciesNet server with file upload support.

Sets up and runs an HTTP server using FastAPI, exposing the SpeciesNet model for remote inference.
It provides REST APIs for making prediction requests to the model, including support for
file uploads and traditional filepath-based requests.
"""

import base64
import io
import tempfile
from typing import List, Optional, Union
from pathlib import Path

from absl import app
from absl import flags
from fastapi import FastAPI, File, UploadFile, HTTPException, Form
from fastapi.responses import JSONResponse
import uvicorn
import PIL.Image
import numpy as np

from speciesnet import DEFAULT_MODEL
from speciesnet import SpeciesNet
from speciesnet.utils import load_rgb_image, PreprocessedImage

_PORT = flags.DEFINE_integer(
    "port",
    8000,
    "Port to run the server on.",
)
_HOST = flags.DEFINE_string(
    "host",
    "0.0.0.0",
    "Host to run the server on.",
)
_WORKERS_PER_DEVICE = flags.DEFINE_integer(
    "workers_per_device",
    1,
    "Number of server replicas per device.",
)
_TIMEOUT = flags.DEFINE_integer(
    "timeout",
    30,
    "Timeout (in seconds) for requests.",
)
_BACKLOG = flags.DEFINE_integer(
    "backlog",
    2048,
    "Maximum number of connections to hold in backlog.",
)
_MODEL = flags.DEFINE_string(
    "model",
    DEFAULT_MODEL,
    "SpeciesNet model to load.",
)
_GEOFENCE = flags.DEFINE_bool(
    "geofence",
    True,
    "Whether to enable geofencing or not.",
)
_EXTRA_FIELDS = flags.DEFINE_list(
    "extra_fields",
    None,
    "Comma-separated list of extra fields to propagate from request to response.",
)


class SpeciesNetServer:
    """Server class for SpeciesNet with file upload support."""

    def __init__(
        self,
        model_name: str,
        geofence: bool = True,
        extra_fields: Optional[List[str]] = None,
    ) -> None:
        """Initializes the SpeciesNet server.

        Args:
            model_name:
                String value identifying the model to be loaded. It can be a Kaggle
                identifier (starting with `kaggle:`), a HuggingFace identifier (starting
                with `hf:`) or a local folder to load the model from.
            geofence:
                Whether to enable geofencing or not. Defaults to `True`.
            extra_fields:
                List of extra fields to propagate from request to response.
        """
        self.model_name = model_name
        self.geofence = geofence
        self.extra_fields = extra_fields or []
        self.model = None
        self.app = FastAPI(title="SpeciesNet API", version="1.0.0")
        self._setup_routes()

    def _setup_routes(self):
        """Setup API routes."""
        
        @self.app.post("/predict")
        async def predict_filepath(request: dict):
            """Traditional predict endpoint using filepaths."""
            try:
                # Validate request format
                if "instances" not in request:
                    raise HTTPException(status_code=400, detail="Missing 'instances' field in request")
                
                for instance in request["instances"]:
                    if "filepath" not in instance:
                        raise HTTPException(status_code=400, detail="Missing 'filepath' field in instance")
                
                # Run prediction
                predictions_dict = self.model.predict(instances_dict=request)
                return self._propagate_extra_fields(request, predictions_dict)
                
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.post("/predict_upload")
        async def predict_upload(
            files: List[UploadFile] = File(...),
            country: Optional[str] = Form(None),
            admin1_region: Optional[str] = Form(None),
            latitude: Optional[float] = Form(None),
            longitude: Optional[float] = Form(None),
        ):
            """Predict endpoint for uploaded image files."""
            try:
                instances = []
                
                for i, file in enumerate(files):
                    if not file.content_type.startswith('image/'):
                        raise HTTPException(
                            status_code=400, 
                            detail=f"File {file.filename} is not an image"
                        )
                    
                    # Read image data
                    image_data = await file.read()
                    
                    # Create temporary file
                    with tempfile.NamedTemporaryFile(delete=False, suffix=f"_{i}.jpg") as temp_file:
                        temp_file.write(image_data)
                        temp_file_path = temp_file.name
                    
                    # Create instance dict
                    instance = {"filepath": temp_file_path}
                    
                    # Add optional location data
                    if country:
                        instance["country"] = country
                    if admin1_region:
                        instance["admin1_region"] = admin1_region
                    if latitude is not None:
                        instance["latitude"] = latitude
                    if longitude is not None:
                        instance["longitude"] = longitude
                    
                    instances.append(instance)
                
                request = {"instances": instances}
                
                # Run prediction
                predictions_dict = self.model.predict(instances_dict=request)
                
                # Clean up temporary files
                for instance in instances:
                    try:
                        Path(instance["filepath"]).unlink()
                    except:
                        pass
                
                return self._propagate_extra_fields(request, predictions_dict)
                
            except Exception as e:
                # Clean up temporary files on error
                for instance in instances:
                    try:
                        Path(instance["filepath"]).unlink()
                    except:
                        pass
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.post("/predict_base64")
        async def predict_base64(request: dict):
            """Predict endpoint for base64 encoded images."""
            try:
                if "instances" not in request:
                    raise HTTPException(status_code=400, detail="Missing 'instances' field in request")
                
                instances = []
                
                for i, instance_data in enumerate(request["instances"]):
                    if "image_data" not in instance_data:
                        raise HTTPException(status_code=400, detail="Missing 'image_data' field in instance")
                    
                    # Decode base64 image
                    try:
                        image_bytes = base64.b64decode(instance_data["image_data"])
                        image = PIL.Image.open(io.BytesIO(image_bytes))
                        image = image.convert("RGB")
                    except Exception as e:
                        raise HTTPException(status_code=400, detail=f"Invalid image data: {str(e)}")
                    
                    # Create temporary file
                    with tempfile.NamedTemporaryFile(delete=False, suffix=f"_{i}.jpg") as temp_file:
                        image.save(temp_file, format="JPEG")
                        temp_file_path = temp_file.name
                    
                    # Create instance dict
                    instance = {"filepath": temp_file_path}
                    
                    # Add optional location data
                    if "country" in instance_data:
                        instance["country"] = instance_data["country"]
                    if "admin1_region" in instance_data:
                        instance["admin1_region"] = instance_data["admin1_region"]
                    if "latitude" in instance_data:
                        instance["latitude"] = instance_data["latitude"]
                    if "longitude" in instance_data:
                        instance["longitude"] = instance_data["longitude"]
                    
                    instances.append(instance)
                
                request_dict = {"instances": instances}
                
                # Run prediction
                predictions_dict = self.model.predict(instances_dict=request_dict)
                
                # Clean up temporary files
                for instance in instances:
                    try:
                        Path(instance["filepath"]).unlink()
                    except:
                        pass
                
                return self._propagate_extra_fields(request_dict, predictions_dict)
                
            except Exception as e:
                # Clean up temporary files on error
                for instance in instances:
                    try:
                        Path(instance["filepath"]).unlink()
                    except:
                        pass
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.get("/health")
        async def health_check():
            """Health check endpoint."""
            return {"status": "healthy", "model": self.model_name}

    def _propagate_extra_fields(
        self, instances_dict: dict, predictions_dict: dict
    ) -> dict:
        """Propagate extra fields from request to response."""
        predictions = predictions_dict["predictions"]
        new_predictions = {p["filepath"]: p for p in predictions}
        for instance in instances_dict["instances"]:
            for field in self.extra_fields:
                if field in instance:
                    new_predictions[instance["filepath"]][field] = instance[field]
        return {"predictions": list(new_predictions.values())}

    def load_model(self):
        """Load the SpeciesNet model."""
        self.model = SpeciesNet(self.model_name, geofence=self.geofence)

    def run(self, host: str = "0.0.0.0", port: int = 8000, workers: int = 1, timeout: int = 30, backlog: int = 2048):
        """Run the server."""
        uvicorn.run(
            self.app, 
            host=host, 
            port=port,
            workers=workers,
            timeout_keep_alive=timeout,
            backlog=backlog
        )


def main(argv: list[str]) -> None:
    del argv  # Unused.

    server = SpeciesNetServer(
        model_name=_MODEL.value,
        geofence=_GEOFENCE.value,
        extra_fields=_EXTRA_FIELDS.value,
    )
    
    print(f"Loading model: {_MODEL.value}")
    server.load_model()
    print("Model loaded successfully!")
    
    print(f"Starting server on {_HOST.value}:{_PORT.value}")
    print(f"Workers per device: {_WORKERS_PER_DEVICE.value}")
    print(f"Timeout: {_TIMEOUT.value}s")
    print(f"Backlog: {_BACKLOG.value}")
    server.run(
        host=_HOST.value, 
        port=_PORT.value,
        workers=_WORKERS_PER_DEVICE.value,
        timeout=_TIMEOUT.value,
        backlog=_BACKLOG.value
    )


if __name__ == "__main__":
    app.run(main) 