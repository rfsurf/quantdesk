"""
Repository 抽象基类
定义所有 Repository 的统一 CRUD 接口。
Stage 1: 内存实现 | Stage 2: PostgreSQL 实现
"""

from abc import ABC, abstractmethod
from typing import Optional, Any


class BaseRepository(ABC):
    """通用 CRUD 抽象，所有 Repo 继承此类"""

    @abstractmethod
    def create(self, entity: dict) -> dict:
        """创建实体，返回创建的实体"""
        ...

    @abstractmethod
    def get(self, entity_id: str) -> Optional[dict]:
        """按 ID 获取实体"""
        ...

    @abstractmethod
    def update(self, entity_id: str, **fields) -> Optional[dict]:
        """更新实体字段"""
        ...

    @abstractmethod
    def delete(self, entity_id: str) -> bool:
        """删除实体，返回是否成功"""
        ...

    @abstractmethod
    def list(self, **filters) -> list[dict]:
        """按过滤条件列出实体"""
        ...
