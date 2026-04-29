from django.contrib import admin
from .models import Document, UserMemory, ChatHistory , CustomUser
from .rag_engine import rag_engine
import os

@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ('file', 'uploaded_at', 'is_processed')
    actions = ['process_documents']

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        # Process the document immediately upon upload
        if not obj.is_processed:
            self.process_file(obj)

    def process_file(self, obj):
        try:
            file_path = obj.file.path
            rag_engine.ingest_document(file_path)
            obj.is_processed = True
            obj.save()
        except Exception as e:
            print(f"Error processing document {obj.file.name}: {e}")

    @admin.action(description='Re-process selected documents')
    def process_documents(self, request, queryset):
        for doc in queryset:
            self.process_file(doc)
        self.message_user(request, "Selected documents have been re-indexed.")

admin.site.register(UserMemory)
admin.site.register(ChatHistory)


@admin.register(CustomUser)
class CustomUserAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'otp')
    search_fields = ('name', 'email')