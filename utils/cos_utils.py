import logging
import uuid
from datetime import datetime
from io import BytesIO

from qcloud_cos import CosConfig, CosS3Client

from config import config

logger = logging.getLogger(__name__)


cos_config = CosConfig(
    Region=config.COS_REGION,
    SecretId=config.COS_SECRET_ID,
    SecretKey=config.COS_SECRET_KEY,
    Domain=config.COS_DOMAIN,
)
_COS_CLIENT = CosS3Client(cos_config)


def _gen_key() -> str:
    date = datetime.now().strftime("%Y%m")
    return f"/paas/content_check/{date}/image/{str(uuid.uuid4())}.jpg"


class COSClient:
    @staticmethod
    def upload_file(file: BytesIO, content_type: str | None = None) -> str:
        global _COS_CLIENT
        try:
            img_key = _gen_key()
            resp = _COS_CLIENT.put_object(
                Bucket="dev",  # Bucket 应该与 secret key 绑定, 这里的参数无效
                Body=file,
                Key=img_key,
                EnableMD5=False,
                **({"ContentType": content_type} if content_type else {}),
            )
            etag = resp.get("ETag")
            if not etag:
                raise Exception("put object failed, None etag")
        except Exception as e:
            logger.error(f"put object failed: {type(e), e}")
            raise e

        try:
            return _COS_CLIENT.get_presigned_url(
                Bucket="dev",  # Bucket 应该与 secret key 绑定, 这里的参数无效
                Key=img_key,
                Method="GET",
                Expired=300,
            )
        except Exception as e:
            logger.error(f"get presigned url failed: {type(e), e}")
            raise e
