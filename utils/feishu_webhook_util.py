import json

import httpx


async def send_message(webhook_url: str, message: str):
    content = {"text": f'<at user_id="all"></at> \n{message}'}
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            url=webhook_url,
            headers={"Content-Type": "application/json; charset=utf-8"},
            json={
                "msg_type": "text",
                "content": json.dumps(content),
            },
        )
        if resp.status_code != 200:
            raise Exception
