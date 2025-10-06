import json
from channels.generic.websocket import AsyncWebsocketConsumer
from django.contrib.auth.models import User
from .models import Issue
from asgiref.sync import sync_to_async


# --------------- ASSIGNED ISSUES CONSUMER ----------------

from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

class AssignedIssueConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # Use authenticated user
        self.user = self.scope["user"]
        if self.user.is_anonymous:
            await self.close()
            return

        # Create a user-specific group
        self.group_name = f"user_{self.user.id}_issues"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data):
        """Receive messages from WebSocket"""
        data = json.loads(text_data)
        action = data.get("action")

        if action == "update_status":
            issue_id = data.get("issue_id")
            status = data.get("status")
            if issue_id and status:
                await self.update_issue_status(issue_id, status)

    async def issue_update(self, event):
        """Send updates from channel layer to WebSocket"""
        await self.send(text_data=json.dumps(event))

    @sync_to_async
    def update_issue_status(self, issue_id, status):
        """Update issue in DB and broadcast to group"""
        try:
            issue = Issue.objects.get(id=issue_id, assigned_to=self.user)
            issue.status = status
            issue.save()

            # Broadcast to the user group
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                f"user_{self.user.id}_issues",
                {
                    "type": "issue_update",
                    "issue_id": issue.id,
                    "title": issue.title,
                    "project_name": issue.project.name,
                    "status": issue.status,
                    "due_date": issue.due_date.isoformat() if issue.due_date else None,
                    "priority": issue.priority
                }
            )
        except Issue.DoesNotExist:
            pass
