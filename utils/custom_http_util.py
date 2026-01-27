import asyncio
import json
import re
from io import BytesIO
from typing import BinaryIO, Literal
from urllib.parse import urlencode

import certifi
import pycurl


class Response:
    def __init__(self) -> None:
        self.status_code: int = 0
        self.headers: dict[str, str] = {}
        self.body: BytesIO = BytesIO()

    def set_header(self, header_bytes: bytes) -> None:
        header_line = header_bytes.decode("iso-8859-1")

        if ":" not in header_line:
            return

        name, value = header_line.split(":", 1)
        name = name.strip()
        value = value.strip()

        self.headers[name.lower()] = value

    def json(self):
        content_type = self.headers.get("content-type", "").lower()

        if "application/json" not in content_type:
            raise Exception("Content-Type is not application/json")

        encoding = "iso-8859-1"
        if match := re.search(r"charset=(\S+)", content_type):
            encoding = match.group(1)

        return json.loads(self.body.read().decode(encoding))


# (file_name, file io)
# (file_name, file io, content type)
FormFile = tuple[str, BinaryIO] | tuple[str, BinaryIO, str]


class CustomHTTP:
    def __init__(self):
        self._curl = pycurl.Curl()
        self._curl.setopt(self._curl.CAINFO, certifi.where())

    def close(self):
        self._curl.close()

    async def request(
        self,
        # method: Literal["GET", "POST", "PUT", "DELETE"],
        method: Literal["GET", "POST"],
        url: str,
        interface: str | None = None,
        query_param: dict[str, str] | None = None,
        json_data: dict | None = None,
        form_data: dict[str, str] | None = None,
        form_files: dict[str, FormFile | list[FormFile]] | None = None,
        follow_redirect: bool = False,
        timeout_s: int = 5,
    ) -> Response:
        """
        发出 HTTP 请求

        Args:
            method (Literal["GET", "POST"]): 当前只实现了 GET, POST
            url (str):
            interface (str | None, optional):
                使用的网卡, 例如 "eth0", 为 None 时系统自动选择. Defaults to None.
            query_param (dict[str, str] | None, optional): 查询参数. Defaults to None.
            json_data (dict | None, optional):
                JSON 格式请求体, 与 form_data/form_files 不兼容. Defaults to None.
            form_data (dict[str, str] | None, optional):
                表单数据, 与 json_data 不兼容. Defaults to None.
            form_files (dict[str, FormFile  |  list[FormFile]] | None, optional):
                表单文件, 与 json_data 不兼容. Defaults to None.
                表单示例:
                ```
                resp = await client.request(
                    method="POST",
                    url="http://example.com:8000/post/file",
                    query_param={"query_param": "123"},
                    form_data={"form_key": "safassfsa"},
                    form_files={
                        "file_key": ("test.md", file_0),
                        "file_list_key": [
                            ("test_1.md", file_1),
                            ("test_2.md", file_2, "image/png"),
                        ],
                    }
                )
                ```

            follow_redirect (bool, optional): 是否跟随重定向. Defaults to False.
            timeout_s (int, optional): 超时时间, 单位秒. Defaults to 5.

        Returns:
            Response:
        """
        if method == "GET" and (json_data or form_data or form_files):
            raise ValueError(" HTTP Body is not allowed in GET method")

        if json_data and (form_data or form_files):
            raise ValueError(
                "can not specify json_data and form_data/form_files "
                "at the same time"
            )
        if query_param:
            url += "?" + urlencode(query_param)

        resp = Response()
        if interface:
            self._curl.setopt(self._curl.INTERFACE, interface)
        self._curl.setopt(self._curl.URL, url)
        self._curl.setopt(self._curl.FOLLOWLOCATION, follow_redirect)
        self._curl.setopt(self._curl.TIMEOUT, max(0, timeout_s))
        self._curl.setopt(self._curl.WRITEDATA, resp.body)
        self._curl.setopt(self._curl.HEADERFUNCTION, resp.set_header)

        if method == "POST":
            if json_data:
                self._set_json_body(json_data=json_data)
            elif form_files:
                self._set_form_files(
                    form_data=form_data,
                    form_files=form_files,
                )
            elif form_data:
                self._set_form_data(form_data=form_data)
            else:
                self._curl.setopt(self._curl.POST, 1)
                self._curl.setopt(self._curl.POSTFIELDS, "")

        await asyncio.to_thread(self._curl.perform)

        resp.status_code = self._curl.getinfo(self._curl.RESPONSE_CODE)

        resp.body.seek(0)
        return resp

    def _set_json_body(self, json_data: dict):
        """设置 JSON 格式请求体 (application/json)"""
        post_data = json.dumps(json_data).encode("utf-8")
        self._curl.setopt(
            self._curl.HTTPHEADER,
            [
                "Content-Type: application/json",
                f"Content-Length: {len(post_data)}",
            ],
        )
        self._curl.setopt(self._curl.POSTFIELDS, post_data)

    def _set_form_files(
        self,
        form_data: dict | None,
        form_files: dict[str, FormFile | list[FormFile]],
    ):
        """设置 带文件的表单 格式请求体 (multipart/form-data)"""
        post_data = (
            [(key, value) for key, value in form_data.items()]
            if form_data
            else []
        )

        def _construct_file(key: str, file: FormFile):
            return key, (
                self._curl.FORM_BUFFER,
                file[0],  # name
                self._curl.FORM_BUFFERPTR,
                file[1].read(),  # bytes
                *(
                    [self._curl.FORM_CONTENTTYPE, file[2]]
                    if len(file) == 3
                    else []
                ),
            )

        for key, value in form_files.items():
            if isinstance(value, list):
                for _file in value:
                    post_data.append(_construct_file(key, _file))
            else:
                post_data.append(_construct_file(key, value))

        self._curl.setopt(self._curl.HTTPPOST, post_data)

    def _set_form_data(self, form_data: dict):
        """设置表单格式请求体 (application/x-www-form-urlencoded)"""
        self._curl.setopt(self._curl.POSTFIELDS, urlencode(form_data))
