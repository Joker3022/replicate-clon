from fastapi import FastAPI, File, UploadFile, Form, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from starlette.middleware.cors import CORSMiddleware
from PIL import Image
import os
import subprocess
import uuid
from pydantic import BaseModel

app = FastAPI()

# Setting up CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ImageData(BaseModel):
    input_dir: str
    output_dir: str

@app.get("/")
def home():
    return {"message": "Welcome to the Barbershop API"}

def resize_image(image_path, output_path, size=(1024, 1024)):
    try:
        with Image.open(image_path) as img:
            img = img.resize(size)
            img.save(output_path)
    except IOError as e:
        raise HTTPException(status_code=500, detail=f"Unable to open or process image: {image_path}. Error: {e}")

def process_images_task(file1_data, file2_data, file3_data, input_dir, output_dir):
    os.makedirs(input_dir, exist_ok=True)
    os.makedirs(output_dir, exist_ok=True)
    file_names = ['file1.png', 'file2.png', 'file3.png']
    resized_paths = []

    for index, data in enumerate([file1_data, file2_data, file3_data]):
        filepath = os.path.join(input_dir, file_names[index])
        with open(filepath, 'wb') as f:
            f.write(data)

        resized_path = os.path.join(input_dir, f"resized_{index + 1}.png")
        resize_image(filepath, resized_path)
        resized_paths.append(resized_path)

    sign = "realistic"
    smooth = 5
    vis_mask_output = os.path.join(output_dir, 'output_image.png')

    command = [
        'python', 'main.py',
        '--input_dir', input_dir,
        '--im_path1', 'resized_1.png',
        '--im_path2', 'resized_2.png',
        '--im_path3', 'resized_3.png',
        '--sign', sign,
        '--smooth', str(smooth),
        '--output_dir', output_dir
    ]

    try:
        result = subprocess.run(command, capture_output=True, text=True, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error during processing: {e.stderr}")

@app.post("/process")
async def process_images(
    background_tasks: BackgroundTasks,
    file1: UploadFile = File(...),
    file2: UploadFile = File(...),
    file3: UploadFile = File(...),
    input_dir: str = Form(...),
    output_dir: str = Form(...)
):
    job_id = str(uuid.uuid4())
    file1_data = await file1.read()
    file2_data = await file2.read()
    file3_data = await file3.read()
    input_dir = os.path.join(input_dir)
    output_dir = os.path.join(output_dir, job_id)
    background_tasks.add_task(process_images_task, file1_data, file2_data, file3_data, input_dir, output_dir)
    return {"message": "Processing started", "job_id": job_id}

@app.get("/results/{job_id}")
async def get_results(job_id: str, output_dir: str = Form(...)):
    output_filepath = os.path.join(output_dir, job_id, 'resized_1_resized_2_resized_3_realistic.png')
    if os.path.isfile(output_filepath):
        return FileResponse(output_filepath, media_type='image/png')
    else:
        return {"error": "Results not ready or job ID is incorrect"}
