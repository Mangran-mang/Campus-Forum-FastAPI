from pydantic_settings import BaseSettings,SettingsConfigDict

class Settings(BaseSettings):
    """
    配置类
    BaseSettings(承自 Pydantic 的 BaseModel) 是配置管理的核心基类
    SettingsConfigDict 是用来给 BaseSettings 配置行为的 “规则字典”
    BaseSeetings在实例化后为字段赋值
    """
    model_config = SettingsConfigDict(env_file=".env",extra="ignore")

    JWT_SECRET: str
    JWT_ALGORITHM: str
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: str = ""
    API_KEY: str
    DATABASE_URL: str

Config = Settings()
"""
为什么要实例化Settings
因为实例化它之后,env才会被读
那些字段才会加载
"""