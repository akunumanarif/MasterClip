import os
import time
import requests
from datetime import datetime, timedelta, timezone


class InstagramService:
    BASE = "https://graph.instagram.com/v20.0"

    def __init__(self):
        self.user_id = os.getenv("INSTAGRAM_USER_ID", "")
        self.token = os.getenv("INSTAGRAM_ACCESS_TOKEN", "")
        # Days to delay publishing (0 = publish immediately)
        self.publish_delay_days = int(os.getenv("INSTAGRAM_PUBLISH_DELAY_DAYS", "0"))

    def is_configured(self) -> bool:
        return bool(self.user_id and self.token)

    def upload_reel(self, video_url: str, caption: str) -> str:
        """
        Upload a video as an Instagram Reel via the Graph API.

        Steps:
        1. Create media container (returns container_id)
        2. Poll until container status = FINISHED (max 5 min)
        3. Publish container (returns post_id)
        4. Fetch permalink and return it

        Returns Instagram post permalink URL.
        Raises RuntimeError on failure.
        """
        # Step 1: Create media container
        scheduled = self.publish_delay_days > 0
        publish_time = None
        if scheduled:
            publish_time = datetime.now(timezone.utc) + timedelta(days=self.publish_delay_days)
            print(f"  [Instagram] Scheduling reel for: {publish_time.isoformat()}")
        else:
            print(f"  [Instagram] Creating media container for: {video_url[:80]}...")

        container_params = {
            "video_url": video_url,
            "caption": caption,
            "media_type": "REELS",
            "share_to_feed": "true",
            "access_token": self.token,
        }
        if scheduled and publish_time:
            container_params["published"] = "false"
            container_params["scheduled_publish_time"] = str(int(publish_time.timestamp()))

        res = requests.post(
            f"{self.BASE}/{self.user_id}/media",
            params=container_params,
            timeout=30,
        )
        data = res.json()
        if "error" in data:
            raise RuntimeError(f"Instagram container creation failed: {data['error']}")
        container_id = data["id"]
        print(f"  [Instagram] Container created: {container_id}")

        # Step 2: Poll until FINISHED
        print(f"  [Instagram] Waiting for container to be ready...")
        for attempt in range(36):  # max 6 min (36 × 10s)
            time.sleep(10)
            status_res = requests.get(
                f"{self.BASE}/{container_id}",
                params={
                    "fields": "status_code,status",
                    "access_token": self.token,
                },
                timeout=15,
            )
            status_data = status_res.json()
            status_code = status_data.get("status_code", "")
            print(f"  [Instagram] Container status ({attempt + 1}/36): {status_code}")

            if status_code == "FINISHED":
                break
            elif status_code == "ERROR":
                raise RuntimeError(f"Instagram container processing failed: {status_data}")
            elif status_code == "EXPIRED":
                raise RuntimeError("Instagram media container expired before publish")
        else:
            raise RuntimeError("Instagram container did not finish processing within 6 minutes")

        # Step 3: Publish (or confirm scheduled)
        if scheduled:
            print(f"  [Instagram] Reel scheduled for {self.publish_delay_days} day(s) later, skipping immediate publish")
            post_id = container_id
        else:
            print(f"  [Instagram] Publishing reel...")
            pub_res = requests.post(
                f"{self.BASE}/{self.user_id}/media_publish",
                params={
                    "creation_id": container_id,
                    "access_token": self.token,
                },
                timeout=30,
            )
            pub_data = pub_res.json()
            if "error" in pub_data:
                raise RuntimeError(f"Instagram publish failed: {pub_data['error']}")
            post_id = pub_data["id"]
            print(f"  [Instagram] Published: post_id={post_id}")

        # Step 4: Fetch permalink
        permalink_res = requests.get(
            f"{self.BASE}/{post_id}",
            params={
                "fields": "permalink",
                "access_token": self.token,
            },
            timeout=15,
        )
        permalink_data = permalink_res.json()
        permalink = permalink_data.get("permalink", f"https://www.instagram.com/p/{post_id}/")
        print(f"  [Instagram] Post URL: {permalink}")
        return permalink


instagram_service = InstagramService()
