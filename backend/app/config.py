from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # ========== 智谱 BigModel 官方 API ==========
    # API Key：必填，从环境变量 ZHIPU_API_KEY 读取
    zhipu_api_key: str = ""
    # Base URL：不含 /chat/completions 后缀，llm_client 会自动拼接
    # llm_client._build_payload() 最终请求完整 URL:
    #   {base_url}/chat/completions
    zhipu_base_url: str = "https://open.bigmodel.cn/api/paas/v4"
    # 模型名称
    zhipu_model: str = "glm-4.5-air"
    # 请求超时（秒）
    request_timeout: float = 60.0
    # ========== 数据库 ==========
    database_url: str = "sqlite:///./mindjournal.db"

    class Config:
        env_file = ".env"


settings = Settings()

# ===== 启动时配置诊断日志（打印到后端黑窗口） =====
_api_key_ok = bool(settings.zhipu_api_key and settings.zhipu_api_key.strip())
_base_url = settings.zhipu_base_url.rstrip("/")
_completions_url = f"{_base_url}/chat/completions"
_model = settings.zhipu_model
_timeout = settings.request_timeout

print("=" * 60)
print("[CONFIG] MindJournal AI - 智谱 BigModel 官方 API")
print("=" * 60)
print(f"[CONFIG] provider       : zhipu (BigModel)")
print(f"[CONFIG] base_url       : {_base_url}")
print(f"[CONFIG] completions_url: {_completions_url}")
print(f"[CONFIG] model          : {_model}")
print(f"[CONFIG] request_timeout: {_timeout}s")
print(f"[CONFIG] api_key set    : {_api_key_ok}")
if not _api_key_ok:
    print("[CONFIG] [WARN] ZHIPU_API_KEY not set or empty. LLM calls will fail!")
print("=" * 60)
