from channel.channel import Channel
from common import log
from flask import request, jsonify
import threading

class WebChannel(Channel):
    def __init__(self):
        self.sessions = {}
        self.lock = threading.Lock()

    def startup(self):
        # Web channel不需要主动启动，通过Flask路由调用
        pass

    def handle(self, msg):
        # 在Flask路由中直接处理
        pass

    def get_session(self, session_id):
        """获取或创建会话"""
        with self.lock:
            if session_id not in self.sessions:
                self.sessions[session_id] = {
                    'history': [],
                    'context': {"from_user_id": session_id, "stream": False}
                }
            return self.sessions[session_id]

    def build_reply(self, query, session_id):
        """生成回复并保存历史"""
        session = self.get_session(session_id)
        
        # 添加上下文历史
        context = session['context']
        context['history'] = session['history']
        
        # 生成回复
        reply = super().build_reply_content(query, context)
        
        # 更新历史记录
        session['history'].append({"role": "user", "content": query})
        session['history'].append({"role": "assistant", "content": reply})
        
        # 限制历史长度
        if len(session['history']) > 20:
            session['history'] = session['history'][-20:]
        
        return reply