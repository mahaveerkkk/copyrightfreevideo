"""
Distributed Celery task definition.
"""

from workers.celery_app import celery_app
from core.engine import VideoTransformer

transformer = VideoTransformer()

@celery_app.task(bind=True)
def process_video_task(self, input_path: str, output_path: str, preset_id: str):
    def on_progress(percent: float, stage: str):
        self.update_state(
            state="PROGRESS",
            meta={"progress": percent, "message": stage}
        )

    result = transformer.process(
        input_path=input_path,
        output_path=output_path,
        preset_id=preset_id,
        progress_callback=on_progress
    )
    return result
