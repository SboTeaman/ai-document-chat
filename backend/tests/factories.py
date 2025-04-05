import factory
from django.contrib.auth import get_user_model

from apps.authentication.models import AuditLog
from apps.chat.models import ChatMessage, ChatSession
from apps.collections.models import Collection
from apps.documents.models import Document, DocumentChunk
from apps.search.models import SearchQuery
from apps.workspaces.models import Workspace, WorkspaceMember

User = get_user_model()


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User

    email = factory.Sequence(lambda n: f"user{n}@example.com")
    full_name = factory.Faker("name")
    password = factory.PostGenerationMethodCall("set_password", "TestPass123!")
    is_active = True


class WorkspaceFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Workspace

    name = factory.Sequence(lambda n: f"Workspace {n}")
    owner = factory.SubFactory(UserFactory)


class WorkspaceMemberFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = WorkspaceMember

    workspace = factory.SubFactory(WorkspaceFactory)
    user = factory.SubFactory(UserFactory)
    role = WorkspaceMember.Role.MEMBER


class CollectionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Collection

    workspace = factory.SubFactory(WorkspaceFactory)
    name = factory.Sequence(lambda n: f"Collection {n}")


class DocumentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Document

    workspace = factory.SubFactory(WorkspaceFactory)
    uploaded_by = factory.SubFactory(UserFactory)
    filename = factory.Sequence(lambda n: f"document_{n}.pdf")
    s3_key = factory.Sequence(lambda n: f"workspaces/1/doc_{n}.pdf")
    mime_type = "application/pdf"
    file_size_bytes = 1024
    status = Document.Status.READY


class DocumentChunkFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = DocumentChunk

    document = factory.SubFactory(DocumentFactory)
    chunk_index = factory.Sequence(lambda n: n)
    content = factory.Faker("paragraph")
    token_count = 150
    embedding = factory.List([factory.Faker("pyfloat", min_value=-1, max_value=1) for _ in range(768)])


class ChatSessionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ChatSession

    workspace = factory.SubFactory(WorkspaceFactory)
    user = factory.SubFactory(UserFactory)
    title = factory.Sequence(lambda n: f"Session {n}")


class ChatMessageFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ChatMessage

    session = factory.SubFactory(ChatSessionFactory)
    role = ChatMessage.Role.USER
    content = factory.Faker("sentence")


class SearchQueryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = SearchQuery

    workspace = factory.SubFactory(WorkspaceFactory)
    user = factory.SubFactory(UserFactory)
    query = factory.Faker("sentence")
    result_count = 0


class AuditLogFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = AuditLog

    workspace = factory.SubFactory(WorkspaceFactory)
    user = factory.SubFactory(UserFactory)
    action = "document.upload"
    resource_type = "document"
    resource_id = 1
