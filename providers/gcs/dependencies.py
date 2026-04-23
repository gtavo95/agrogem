from fastapi import Depends
from google.cloud.storage import Bucket

from domain.pest.storage import PestStorage
from providers.gcs.config import get_gcs_bucket
from providers.gcs.pest_storage import GcsPestStorage


def get_pest_storage(bucket: Bucket = Depends(get_gcs_bucket)) -> PestStorage:
    return GcsPestStorage(bucket)
