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
from fastapi.responses import JSONResponse, HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
import uvicorn
import PIL.Image
import numpy as np

from speciesnet import DEFAULT_MODEL
from speciesnet import SpeciesNet
from speciesnet.utils import load_rgb_image, PreprocessedImage

# Only define flags when running as main script, not when imported as module
if __name__ == "__main__":
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
else:
    # When imported as module, create dummy flag objects
    class DummyFlag:
        def __init__(self, value):
            self.value = value
    
    _PORT = DummyFlag(8000)
    _HOST = DummyFlag("0.0.0.0")
    _WORKERS_PER_DEVICE = DummyFlag(1)
    _TIMEOUT = DummyFlag(30)
    _BACKLOG = DummyFlag(2048)
    _MODEL = DummyFlag(DEFAULT_MODEL)
    _GEOFENCE = DummyFlag(True)
    _EXTRA_FIELDS = DummyFlag(None)


# Global variables for server configuration
_MODEL_NAME = None
_GEOFENCE_ENABLED = True
_EXTRA_FIELDS_LIST = []

# Global app instance for multi-worker support
fastapi_app = None

# Create the app instance at module level for multi-worker support
def _create_app_for_workers():
    """Create app instance for multi-worker support."""
    global _MODEL_NAME, _GEOFENCE_ENABLED, _EXTRA_FIELDS_LIST
    return create_app()

def create_app():
    """Create and configure the FastAPI application."""
    app = FastAPI(title="SpeciesNet API", version="1.0.0")
    
    # Mount static files
    front_dir = Path(__file__).parent.parent.parent / "front"
    if front_dir.exists():
        app.mount("/static", StaticFiles(directory=str(front_dir)), name="static")
    
    # Global model instance
    model = None
    
    def load_model():
        """Load the SpeciesNet model."""
        nonlocal model
        if model is None:
            model = SpeciesNet(_MODEL_NAME, geofence=_GEOFENCE_ENABLED)
        return model
    
    def propagate_extra_fields(instances_dict: dict, predictions_dict: dict) -> dict:
        """Propagate extra fields from request to response."""
        predictions = predictions_dict["predictions"]
        new_predictions = {p["filepath"]: p for p in predictions}
        for instance in instances_dict["instances"]:
            for field in _EXTRA_FIELDS_LIST:
                if field in instance:
                    new_predictions[instance["filepath"]][field] = instance[field]
        return {"predictions": list(new_predictions.values())}
    
    @app.post("/predict")
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
            model_instance = load_model()
            predictions_dict = model_instance.predict(instances_dict=request)
            return propagate_extra_fields(request, predictions_dict)
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.post("/predict_upload")
    async def predict_upload(
        files: List[UploadFile] = File(...),
        country: Optional[str] = Form(None),
        admin1_region: Optional[str] = Form(None),
        latitude: Optional[float] = Form(None),
        longitude: Optional[float] = Form(None),
    ):
        """Predict endpoint for uploaded image files."""
        instances = []
        try:
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
            model_instance = load_model()
            predictions_dict = model_instance.predict(instances_dict=request)
            
            # Clean up temporary files
            for instance in instances:
                try:
                    Path(instance["filepath"]).unlink()
                except:
                    pass
            
            return propagate_extra_fields(request, predictions_dict)
            
        except Exception as e:
            # Clean up temporary files on error
            for instance in instances:
                try:
                    Path(instance["filepath"]).unlink()
                except:
                    pass
            raise HTTPException(status_code=500, detail=str(e))

    @app.post("/predict_base64")
    async def predict_base64(request: dict):
        """Predict endpoint for base64 encoded images."""
        instances = []
        try:
            if "instances" not in request:
                raise HTTPException(status_code=400, detail="Missing 'instances' field in request")
            
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
            model_instance = load_model()
            predictions_dict = model_instance.predict(instances_dict=request_dict)
            
            # Clean up temporary files
            for instance in instances:
                try:
                    Path(instance["filepath"]).unlink()
                except:
                    pass
            
            return propagate_extra_fields(request_dict, predictions_dict)
            
        except Exception as e:
            # Clean up temporary files on error
            for instance in instances:
                try:
                    Path(instance["filepath"]).unlink()
                except:
                    pass
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/")
    async def root():
        """Redirect root path to index.html."""
        return RedirectResponse(url="/static/index.html")



    @app.get("/health")
    async def health_check():
        """Health check endpoint."""
        return {"status": "healthy", "model": _MODEL_NAME}
    
    return app


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
        global _MODEL_NAME, _GEOFENCE_ENABLED, _EXTRA_FIELDS_LIST
        _MODEL_NAME = model_name
        _GEOFENCE_ENABLED = geofence
        _EXTRA_FIELDS_LIST = extra_fields or []
        self.model_name = model_name
        self.geofence = geofence
        self.extra_fields = extra_fields or []
        self.app = create_app()

    def run(self, host: str = "0.0.0.0", port: int = 8000, workers: int = 1, timeout: int = 30, backlog: int = 2048):
        """Run the server."""
        # For multiple workers, we need to use import string format
        if workers > 1:
            # Set environment variables for the workers
            import os
            os.environ["SPECIESNET_MODEL"] = self.model_name
            os.environ["SPECIESNET_GEOFENCE"] = str(self.geofence)
            os.environ["SPECIESNET_EXTRA_FIELDS"] = ",".join(self.extra_fields) if self.extra_fields else ""
            
            uvicorn.run(
                "run_server_with_upload:fastapi_app",
                host=host, 
                port=port,
                workers=workers,
                timeout_keep_alive=timeout,
                backlog=backlog
            )
        else:
            # Single worker can use the app object directly
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
    
    # Set global app for multi-worker support
    global fastapi_app
    fastapi_app = server.app
    
    print(f"Loading model: {_MODEL.value}")
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
else:
    # When imported as a module (for multi-worker support), 
    # we need to set the global variables and create the app
    import os
    
    # Read configuration from environment variables
    _MODEL_NAME = os.environ.get("SPECIESNET_MODEL", DEFAULT_MODEL)
    _GEOFENCE_ENABLED = os.environ.get("SPECIESNET_GEOFENCE", "True").lower() == "true"
    extra_fields_str = os.environ.get("SPECIESNET_EXTRA_FIELDS", "")
    _EXTRA_FIELDS_LIST = extra_fields_str.split(",") if extra_fields_str else []
    
    # Create the app instance
    fastapi_app = _create_app_for_workers() 