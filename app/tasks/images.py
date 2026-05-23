from app.tasks.celery_app import celery_app


@celery_app.task
def process_image_upload(file_path: str, property_id: str):
    """Process and optimize uploaded image."""
    # TODO: Implement WebP optimization and MinIO upload
    return {"file_path": file_path, "property_id": property_id, "status": "processed"}
