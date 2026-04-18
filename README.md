# astrbot-plugin-life-scheduler

AstrBot MiniMax生图插件 / A Life Scheduler Plugin for AstrBot

> [!NOTE]
> 此插件为 [AstrBot](https://github.com/AstrBotDevs/AstrBot) 的功能扩展，提供生成自拍照指令。
>
> [AstrBot](https://github.com/AstrBotDevs/AstrBot) 是一个智能对话助手，支持 QQ、Telegram、飞书、钉钉、Slack、Discord 等多平台部署，可快速构建个人 AI 助手、企业客服、自动化工作流等应用。

# 功能指令

| 指令 | 说明 |
|------|------|
| `/自拍` | 根据今日穿搭和日程，生成一张 3:4 比例的自拍照 |

# 配置项

| 配置项 | 说明 |
|--------|------|
| `api_base` | MiniMax API 接口地址，如 `https://api.minimaxi.com/v1` |
| `api_key` | MiniMax 接口密钥 |
| `txt2img_model` | 文生图模型，无参考图时使用（如 `image-01`） |
| `img2img_model` | 图生图模型，有参考图时使用（如 `image-01`） |

> 参考图存放路径：`data_dir/ref.png`（存在时走图生图，不存在时走文生图）

# 支持链接

- [AstrBot 官方仓库](https://github.com/AstrBotDevs/AstrBot)
- [AstrBot 插件开发文档（中文）](https://docs.astrbot.app/dev/star/plugin-new.html)
- [AstrBot 插件开发文档（英文）](https://docs.astrbot.app/en/dev/star/plugin-new.html)