from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated


class ChatView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        return Response({'message': 'Not yet implemented'})


class HistoryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response([])

    def delete(self, request):
        from rest_framework import status
        return Response(status=status.HTTP_204_NO_CONTENT)
