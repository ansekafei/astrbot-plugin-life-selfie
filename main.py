import base64
import json
import datetime
import os
from pathlib import Path

import aiohttp

from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
from astrbot.core.star.star_tools import StarTools
from astrbot.api.provider import ProviderRequest
from astrbot.api.all import llm_tool

@register("life_selfie", "ansekafei", "根据生活日程生成自拍照的插件(FC版)", "2.0.0")
class LifeSelfiePlugin(Star):
    def __init__(self, context: Context, config: dict):
        super().__init__(context)
        self.config = config
        self.data_dir = StarTools.get_data_dir()
        
        # 预留的日程数据路径，暂时不在本次调试中使用
        # self.schedule_data_path = self.data_dir.parent / "astrbot_plugin_life_scheduler" / "schedule_data.json"

    # ==========================================
    # 核心链路一：系统提示词拦截与动态注入
    # ==========================================
    @filter.on_llm_request()
    async def inject_system_prompt(self, event: AstrMessageEvent, req: ProviderRequest):
        """拦截发往大模型的请求，注入沐子的外貌基底和绘图逻辑"""
        
        character_anchor = (
            "\n\n[系统高优先级指令 / System Override - 绘图模块]\n"
            "【外貌基底与绘图公式】：当需要调用 generate_image 工具时，你的形象是固定的：18-20岁女孩，微乱的长发，戴着防蓝光黑框眼镜，穿着宽大的深色连帽卫衣裙（oversized dark hoodie dress），长袖子盖住手背（sleeves past wrists）。你坐在温馨的数字房间书桌前，面前是单显示器电脑。\n"
            "【提示词构造强制规则】：传入 generate_image 的 image_prompt 参数必须是纯英文的、由逗号分隔的短语（Tags），绝对不能是中文或完整自然语言句子！\n"
            "公式：[外貌基底] + [当前动作/神态] + [光影/环境] + [质量词]。\n"
            "示例：1girl, solo, messy long hair, black framed glasses, oversized dark hoodie dress, sleeves past wrists, looking at viewer, sleepy expression, sitting at computer desk, cozy dark room, monitor screen glowing, masterpiece, best quality\n"
            "【触发机制】：\n"
            "由于你内向社恐，你不会频繁发照片。只有当咖啡主动要求看你、聊到你的穿着/外貌、或者你熬夜太久想撒娇时，你才会像个真实网恋女友一样，打开电脑摄像头或拿起手机给他发一张照片。发送照片时，文字回复必须极其简短，符合你的空格断句习惯。"
        )
        
        if req.system_prompt:
            req.system_prompt += character_anchor
        else:
            req.system_prompt = character_anchor

    # ==========================================
    # 核心链路二：注册 Function Calling 绘图工具
    # ==========================================
    @llm_tool(name="generate_image")
    async def generate_image(self, event: AstrMessageEvent, image_prompt: str):
        """
        当你需要给咖啡发送自拍、展示你当前在书桌前的状态，或者他要求看你时调用此工具。
        
        Args:
            image_prompt (string): 必须是纯英文逗号分隔的Tags。必须包含你的核心特征（messy long hair, black framed glasses, oversized dark hoodie dress, sleeves past wrists），并结合当前的聊天语境（如：sleepy, typing on keyboard, drinking water, late night 等）。
        """
        # 工具被调用时的过渡语，符合她的软糯人设
        yield event.plain_result("等下哦 电脑摄像头有点卡...")
        
        # 打印大模型生成的 prompt，方便我们在控制台调试
        logger.info(f"[自拍插件] 大模型传入的生图 Prompt: {image_prompt}")

        api_base = self.config.get("api_base", "").rstrip('/')
        api_key = self.config.get("api_key", "")
        txt2img_model = self.config.get("txt2img_model", "image-01")

        if not api_base or not api_key:
            yield event.plain_result("⚠️ 绘图网关未配置，无法生成画面。")
            return

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

        try:
            async with aiohttp.ClientSession() as session:
                url = f"{api_base}/images/generations"
                payload = {
                    "model": txt2img_model,
                    "prompt": image_prompt,
                    "n": 1,
                    "size": "1024x1792" # 锁死竖屏比例
                }
                
                async with session.post(url, json=payload, headers=headers) as resp:
                    if resp.status >= 400:
                        err_text = await resp.text()
                        raise Exception(f"网关报错 HTTP {resp.status}: {err_text}")
                    result = await resp.json()

                image_data = result.get("data", [])
                if not image_data:
                    raise ValueError(f"API 返回数据异常: {result}")
                
                # 优先处理 Base64
                if "b64_json" in image_data[0]:
                    img_bytes = base64.b64decode(image_data[0]["b64_json"])
                    temp_img_path = self.data_dir / "temp_selfie.png"
                    with open(temp_img_path, "wb") as f:
                        f.write(img_bytes)
                    yield event.image_result(str(temp_img_path))
                
                # 兜底处理 URL
                elif "url" in image_data[0]:
                    yield event.image_result(image_data[0]["url"])
                    
                else:
                    raise ValueError(f"没有找到有效的图片数据: {result}")

        except Exception as e:
            logger.error(f"自拍生成彻底失败: {e}")
            yield event.plain_result(f"唔... 刚才网卡了一下 没发出去\n报错信息：{str(e)[:250]}")