"""初始化内置管理员账号"""

from datetime import UTC, datetime

from sqlalchemy import func, select

from app.core.config import settings
from app.core.database import async_session_factory
from app.core.security import hash_password
from app.models.system_config import SystemConfig
from app.models.user import User

DEFAULT_ADMIN = {
    "name": "admin",
    "email": "admin@edumind.cn",
}


async def ensure_admin():
    """如果系统中没有管理员，创建一个默认管理员（必须改密码）"""
    async with async_session_factory() as db:
        result = await db.execute(select(func.count(User.id)).where(User.role == "admin"))
        admin_count = result.scalar()

        if admin_count > 0:
            # 清理旧版因 email 格式错误创建的管理员
            await db.execute(select(User).where(User.email == "admin@edumind.local"))
            old = (await db.execute(select(User).where(User.email == "admin@edumind.local"))).scalar_one_or_none()
            if old:
                await db.delete(old)
                await db.commit()
                print("  🧹 已清理旧版邮箱的管理员")
            else:
                print("  ✅ 管理员已存在，跳过初始化")
            return

        if not settings.default_admin_password:
            print("  ⚠️  未配置 DEFAULT_ADMIN_PASSWORD，跳过内置管理员创建")
            print("  ℹ️  首位自助注册用户仍会自动成为管理员")
            return

        admin = User(
            name=DEFAULT_ADMIN["name"],
            email=DEFAULT_ADMIN["email"],
            password_hash=hash_password(settings.default_admin_password),
            role="admin",
            must_change_password=True,
            learner_profile={},
            created_at=datetime.now(UTC),
        )
        db.add(admin)
        await db.flush()

        # 创建默认系统配置
        config_result = await db.execute(select(SystemConfig).limit(1))
        if not config_result.scalar_one_or_none():
            sys_config = SystemConfig(updated_by=admin.id)
            db.add(sys_config)

        await db.commit()
        print(f"  ✅ 内置管理员已创建: {DEFAULT_ADMIN['email']}")
        print("  ⚠️  首次登录请使用 DEFAULT_ADMIN_PASSWORD，并立即修改密码！")
