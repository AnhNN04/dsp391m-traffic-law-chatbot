from datetime import datetime, timezone
from typing import List, Optional

from sqlmodel import Session, select

from app.domain.models.user import User
from app.domain.models.chat import ChatSession


class PostgresRepository:
    """
    Repository layer chịu trách nhiệm thao tác với PostgreSQL thông qua SQLModel.

    - Không chứa business logic
    - Chỉ thực hiện CRUD và truy vấn dữ liệu
    """

    def __init__(self, session: Session) -> None:
        """
        Khởi tạo repository với SQLModel Session.

        Args:
            session (Session): Database session (được inject từ dependency)
        """
        self.session = session

    # ---------------------------------------------------------------------
    # User operations
    # ---------------------------------------------------------------------

    def create_user(self, user: User) -> User:
        """
        Tạo mới một user trong database.

        Args:
            user (User): Entity User đã được validate trước đó

        Returns:
            User: User sau khi được persist (đã có id)
        """
        self.session.add(user)
        self.session.commit()
        self.session.refresh(user)
        return user

    def get_user_by_email(self, email: str) -> Optional[User]:
        """
        Lấy user theo email.

        Args:
            email (str): Email cần tìm

        Returns:
            Optional[User]: User nếu tồn tại, ngược lại None
        """
        statement = select(User).where(User.email == email)
        return self.session.exec(statement).first()

    # ---------------------------------------------------------------------
    # Chat session operations
    # ---------------------------------------------------------------------

    def create_chat_session(
        self,
        user_id: int,
        title: str = "New Chat",
    ) -> ChatSession:
        """
        Tạo một chat session mới cho user.

        Args:
            user_id (int): ID của user sở hữu session
            title (str, optional): Tiêu đề chat. Mặc định là "New Chat"

        Returns:
            ChatSession: ChatSession vừa được tạo
        """
        chat_session = ChatSession(
            user_id=user_id,
            title=title,
            history=[],
        )

        self.session.add(chat_session)
        self.session.commit()
        self.session.refresh(chat_session)

        return chat_session

    def get_user_chat_sessions(self, user_id: int) -> List[ChatSession]:
        """
        Lấy danh sách chat session của một user, sắp xếp theo updated_at giảm dần.

        Args:
            user_id (int): ID của user

        Returns:
            List[ChatSession]: Danh sách chat session
        """
        statement = (
            select(ChatSession)
            .where(ChatSession.user_id == user_id)
            .order_by(ChatSession.updated_at.desc())
        )

        return self.session.exec(statement).all()

    def get_chat_session(self, session_id: int) -> Optional[ChatSession]:
        """
        Lấy một chat session theo ID.

        Args:
            session_id (int): ID của chat session

        Returns:
            Optional[ChatSession]: ChatSession nếu tồn tại, ngược lại None
        """
        return self.session.get(ChatSession, session_id)

    def update_chat_history(
        self,
        session_id: int,
        new_history: list,
    ) -> Optional[ChatSession]:
        """
        Cập nhật lịch sử chat và timestamp của chat session.

        Args:
            session_id (int): ID của chat session
            new_history (list): Lịch sử chat mới (đã xử lý ở service layer)

        Returns:
            Optional[ChatSession]: ChatSession sau khi update, hoặc None nếu không tồn tại
        """
        chat_session = self.get_chat_session(session_id)

        if chat_session is None:
            return None

        chat_session.history = new_history
        chat_session.updated_at = datetime.now(timezone.utc)

        self.session.add(chat_session)
        self.session.commit()
        self.session.refresh(chat_session)

        return chat_session
    def delete_chat_session(self, session_id: int) -> Optional[ChatSession]:
        """ Xóa một chat session theo ID.  
        Args:
            session_id (int): ID của chat session
        Returns:
            Optional[ChatSession]: ChatSession đã bị xóa, hoặc None nếu không tồn tại
        """
        chat_session = self.get_chat_session(session_id)

        if chat_session is None:
            return None

        self.session.delete(chat_session)
        self.session.commit()

        return chat_session
