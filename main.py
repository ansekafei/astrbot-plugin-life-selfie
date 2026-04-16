import base64
import datetime
import json
import os
from pathlib import Path

import aiohttp

from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
# 修复：导入正确的路径工具类
from astrbot.core.star.star_tools import StarTools

@register("life_selfie", "ansekafei", "根据生活日程生成自拍照的插件", "1.0.0")
class LifeSelfiePlugin(Star):
    def __init__(self, context: Context, config: dict):
        super().__init__(context)
        self.config = config
        
        # 修复：使用 StarTools 获取当前插件的独立数据目录
        self.data_dir = StarTools.get_data_dir()
        
        # 跨插件读取数据：向上一级找到 plugins 目录，再进入日程插件目录
        self.schedule_data_path = self.data_dir.parent / "astrbot_plugin_life_scheduler" / "schedule_data.json"

    @filter.command("自拍")
    async def generate_selfie(self, event: AstrMessageEvent):
        """生成一张带有今日穿搭和日程的自拍照"""
        yield event.plain_result("正在整理衣服找角度，请稍等哦~")

        # 读取配置项
        api_base = self.config.get("api_base", "").rstrip('/')
        api_key = self.config.get("api_key", "")
        txt2img_model = self.config.get("txt2img_model", "image-01")
        img2img_model = self.config.get("img2img_model", "image-01")

        if not api_base or not api_key:
            yield event.plain_result("📸 自拍功能未初始化，请先在网页管理后台配置 API 接口地址和 Key 哦~")
            return

        # 安全地从 JSON 文件读取今日数据
        today_str = datetime.datetime.now().strftime("%Y-%m-%d")
        outfit = "日常休闲装"
        schedule = "正在放松休息"
        
        try:
            if self.schedule_data_path.exists():
                with open(self.schedule_data_path, "r", encoding="utf-8") as f:
                    schedule_data = json.load(f)
                    if today_str in schedule_data:
                        outfit = schedule_data[today_str].get("outfit", outfit)
                        schedule = schedule_data[today_str].get("schedule", schedule)
        except Exception as e:
            logger.error(f"读取日程数据失败: {e}")

        # 组装 Prompt
        prompt = (
            f"Selfie perspective, wearing {outfit}, doing {schedule}, "
            f"casual selfie photo, natural lighting, upper body portrait, masterpiece, highly detailed"
        )

        ref_image_path = self.data_dir / "ref.png"
        has_ref_image = ref_image_path.exists()

        headers = {
            "Authorization": f"Bearer {api_key}"
        }

        try:
            async with aiohttp.ClientSession() as session:
                if not has_ref_image:
                    # ===== 场景 A：无参考图，走标准文生图 =====
                    url = f"{api_base}/images/generations"
                    headers["Content-Type"] = "application/json"
                    payload = {
                        "model": txt2img_model,
                        "prompt": prompt,
                        "n": 1,
                        "size": "1024x1024"
                    }
                    async with session.post(url, json=payload, headers=headers) as resp:
                        if resp.status >= 400:
                            err_text = await resp.text()
                            raise Exception(f"文生图报错 HTTP {resp.status}: {err_text}")
                        result = await resp.json()
                else:
                    # ===== 场景 B：有参考图，走标准图生图/编辑 =====
                    url = f"{api_base}/images/edits"
                    form_data = aiohttp.FormData()
                    form_data.add_field('image', open(ref_image_path, 'rb'), filename='ref.png', content_type='image/png')
                    form_data.add_field('prompt', prompt)
                    form_data.add_field('model', img2img_model)
                    form_data.add_field('n', '1')
                    form_data.add_field('size', '1024x1024')
                    
                    async with session.post(url, data=form_data, headers=headers) as resp:
                        if resp.status >= 400:
                            err_text = await resp.text()
                            raise Exception(f"图生图报错 HTTP {resp.status}: {err_text}")
                        result = await resp.json()

                # 使用标准 OpenAI 返回格式解析
                image_data = result.get("data", [])
                if not image_data:
                    raise ValueError(f"API 返回数据异常: {result}")
                
                # 处理 Base64 格式的返回
                if "b64_json" in image_data[0]:
                    img_bytes = base64.b64decode(image_data[0]["b64_json"])
                    # 将图片暂时保存在插件目录下
                    temp_img_path = self.data_dir / "temp_selfie.png"
                    with open(temp_img_path, "wb") as f:
                        f.write(img_bytes)
                    
                    # 发送本地图片
                    yield event.image_result(str(temp_img_path))
                    
                # 兼容传统的 URL 返回
                elif "url" in image_data[0]:
                    yield event.image_result(image_data[0]["url"])
                    
                else:
                    raise ValueError(f"没有找到有效的图片数据: {result}")

        except Exception as e:
            logger.error(f"自拍生成彻底失败: {e}")
            # 把网关的真实报错直接发到聊天框里，方便一眼看穿！
            yield event.plain_result(f"网关抗议啦！报错信息：\n{str(e)[:250]}")
