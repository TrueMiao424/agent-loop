from rest_framework.permissions import AllowAny
from rest_framework.views import APIView

from apps.common.response import ApiResponse
from apps.webhook.dto.serializers import WebhookSerializer
from apps.webhook.service.webhook_service import WebhookService


class WebhookListCreateView(APIView):
    def get(self, request):
        from apps.common.util.pagination import page_payload, parse_page_params

        page, page_size = parse_page_params(request)
        messages, total = WebhookService.list_messages_page(page, page_size)
        return ApiResponse.ok(
            page_payload(
                WebhookSerializer(messages, many=True).data,
                total,
                page,
                page_size,
            )
        )

    def post(self, request):
        msg = WebhookService.inject_message(request.data)
        return ApiResponse.ok(WebhookSerializer(msg).data)


class FeishuWebhookView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        payload = request.data if isinstance(request.data, dict) else {}
        # 飞书 HTTP 回调校验要求裸返回 {"challenge": "..."}，不能包一层 ApiResponse
        if payload.get("type") == "url_verification":
            from rest_framework.response import Response

            return Response({"challenge": payload.get("challenge")})
        result = WebhookService.handle_feishu_event(payload)
        return ApiResponse.ok(result)


class FeishuLongConnectionStatusView(APIView):
    def get(self, request):
        from apps.webhook.service.feishu_ws_service import get_status

        return ApiResponse.ok(get_status())


class FeishuLongConnectionLogsView(APIView):
    def get(self, request):
        from apps.webhook.service.feishu_ws_service import get_logs

        return ApiResponse.ok(get_logs())


class FeishuLongConnectionRestartView(APIView):
    def post(self, request):
        from apps.webhook.service.feishu_ws_service import get_status, restart_feishu_ws

        restart_feishu_ws()
        return ApiResponse.ok(get_status(), msg="长连接已重新连接")


class FeishuChatsListView(APIView):
    def get(self, request):
        from apps.webhook.client.feishu_client import FeishuClient

        try:
            items = FeishuClient.list_bot_chats()
        except ValueError as exc:
            return ApiResponse.fail(str(exc))
        except Exception as exc:
            return ApiResponse.fail(f"获取群列表失败：{exc}")
        return ApiResponse.ok(items)
