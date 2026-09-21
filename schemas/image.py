from pydantic import BaseModel, ConfigDict


# ============ 输出模型（白名单）============

class ImageOut(BaseModel):
    """图片输出

    ## comment
    ### 只声明这三个字段，是【沿用现有响应形状】
    上传与查询接口现在返回的就是 {"id", "filename", "target_type"}，
    所以模型只声明这三个，前端零改动。
    注意这和"漏写字段"不同：这里是主动选择只暴露这三个。
    ### 为什么不给 target_id / author_uid
    调用方本来就知道自己传的 target_type / target_id（都在 URL 路径里），
    回显它们属于重复；author_uid 对展示也没用。
    将来前端确实需要（比如"这张图属于谁"）再加，改一处即可。
    ### 为什么没有 author 关系
    Image 上有 author 关系，但图片场景用不到作者信息。
    带上它就需要额外预加载，而 crud/image.py 目前没有 selectinload(Image.author)——
    真读了反而会触发异步懒加载 → MissingGreenlet → 500。
    用不到的关系不要写进输出模型，这是最省事的防线。
    """
    model_config = ConfigDict(from_attributes=True)

    id: int
    filename: str
    target_type: str
