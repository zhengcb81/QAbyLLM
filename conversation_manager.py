#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
对话管理器
支持多轮对话的上下文管理和记忆
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from enum import Enum
import time
import json
import re
from dataclasses import dataclass
from collections import deque

logger = logging.getLogger(__name__)

class ConversationState(Enum):
    """对话状态枚举"""
    ACTIVE = "active"
    COMPLETED = "completed"
    ABANDONED = "abandoned"
    ERROR = "error"

@dataclass
class Message:
    """对话消息"""
    role: str  # user, assistant, system
    content: str
    timestamp: str
    message_id: str
    metadata: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'role': self.role,
            'content': self.content,
            'timestamp': self.timestamp,
            'message_id': self.message_id,
            'metadata': self.metadata
        }

@dataclass
class Conversation:
    """对话会话"""
    conversation_id: str
    user_id: str
    created_at: str
    updated_at: str
    state: ConversationState
    messages: List[Message]
    metadata: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'conversation_id': self.conversation_id,
            'user_id': self.user_id,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'state': self.state.value,
            'messages': [msg.to_dict() for msg in self.messages],
            'metadata': self.metadata
        }

class ConversationManager:
    """对话管理器"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.conversations: Dict[str, Conversation] = {}
        self.max_history = self.config.get('max_history', 20)
        self.session_timeout = self.config.get('session_timeout_minutes', 30)
        self._cleanup_interval = self.config.get('cleanup_interval_minutes', 5)
        self._last_cleanup = time.time()
    
    def create_conversation(self, user_id: str, **metadata) -> Conversation:
        """创建新对话"""
        conversation_id = self._generate_conversation_id()
        now = datetime.now().isoformat()
        
        conversation = Conversation(
            conversation_id=conversation_id,
            user_id=user_id,
            created_at=now,
            updated_at=now,
            state=ConversationState.ACTIVE,
            messages=[],
            metadata=metadata or {}
        )
        
        self.conversations[conversation_id] = conversation
        logger.info(f"创建新对话: {conversation_id} (用户: {user_id})")
        
        return conversation
    
    def add_message(self, 
                   conversation_id: str, 
                   role: str, 
                   content: str, 
                   **metadata) -> Optional[Message]:
        """添加消息到对话"""
        if conversation_id not in self.conversations:
            logger.warning(f"对话不存在: {conversation_id}")
            return None
        
        conversation = self.conversations[conversation_id]
        
        # 检查对话状态
        if conversation.state != ConversationState.ACTIVE:
            logger.warning(f"对话状态为 {conversation.state.value}, 无法添加消息")
            return None
        
        # 创建消息
        message = Message(
            role=role,
            content=content,
            timestamp=datetime.now().isoformat(),
            message_id=self._generate_message_id(),
            metadata=metadata or {}
        )
        
        # 添加到消息列表
        conversation.messages.append(message)
        
        # 限制历史消息数量
        if len(conversation.messages) > self.max_history:
            # 保留系统消息和最近的用户/助手消息
            kept_messages = []
            for msg in conversation.messages:
                if msg.role == 'system' or len(kept_messages) < self.max_history // 2:
                    kept_messages.append(msg)
            
            # 添加最新的消息
            recent_messages = conversation.messages[-(self.max_history - len(kept_messages)):]
            conversation.messages = kept_messages + recent_messages
        
        # 更新对话时间
        conversation.updated_at = datetime.now().isoformat()
        
        logger.debug(f"添加消息到对话 {conversation_id}: {role} - {content[:50]}...")
        
        return message
    
    def get_conversation(self, conversation_id: str) -> Optional[Conversation]:
        """获取对话"""
        # 自动清理过期对话
        self._cleanup_expired_conversations()
        
        return self.conversations.get(conversation_id)
    
    def get_conversation_history(self, conversation_id: str, max_messages: Optional[int] = None) -> List[Message]:
        """获取对话历史"""
        conversation = self.get_conversation(conversation_id)
        if not conversation:
            return []
        
        messages = conversation.messages
        if max_messages and max_messages > 0:
            messages = messages[-max_messages:]
        
        return messages
    
    def get_conversation_context(self, conversation_id: str, max_tokens: int = 4000) -> List[Dict[str, str]]:
        """获取对话上下文（适合LLM的格式）"""
        messages = self.get_conversation_history(conversation_id)
        
        # 转换为LLM格式
        llm_messages = []
        current_tokens = 0
        
        for message in reversed(messages):
            message_tokens = self._estimate_tokens(message.content)
            
            # 检查是否超过token限制
            if current_tokens + message_tokens > max_tokens:
                break
            
            llm_messages.insert(0, {
                'role': message.role,
                'content': message.content
            })
            
            current_tokens += message_tokens
        
        return llm_messages
    
    def update_conversation_state(self, conversation_id: str, state: ConversationState) -> bool:
        """更新对话状态"""
        conversation = self.get_conversation(conversation_id)
        if not conversation:
            return False
        
        conversation.state = state
        conversation.updated_at = datetime.now().isoformat()
        
        logger.info(f"更新对话状态: {conversation_id} -> {state.value}")
        return True
    
    def summarize_conversation(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """总结对话"""
        conversation = self.get_conversation(conversation_id)
        if not conversation or not conversation.messages:
            return None
        
        # 提取关键信息
        user_messages = [msg for msg in conversation.messages if msg.role == 'user']
        assistant_messages = [msg for msg in conversation.messages if msg.role == 'assistant']
        
        # 简单的总结逻辑（实际应该使用LLM）
        summary = {
            'total_messages': len(conversation.messages),
            'user_messages': len(user_messages),
            'assistant_messages': len(assistant_messages),
            'first_user_message': user_messages[0].content[:100] + '...' if user_messages else '',
            'last_user_message': user_messages[-1].content[:100] + '...' if user_messages else '',
            'duration_minutes': self._get_conversation_duration(conversation),
            'main_topics': self._extract_topics(conversation.messages)
        }
        
        return summary
    
    def delete_conversation(self, conversation_id: str) -> bool:
        """删除对话"""
        if conversation_id in self.conversations:
            del self.conversations[conversation_id]
            logger.info(f"删除对话: {conversation_id}")
            return True
        return False
    
    def get_user_conversations(self, user_id: str, active_only: bool = True) -> List[Conversation]:
        """获取用户的所有对话"""
        self._cleanup_expired_conversations()
        
        conversations = []
        for conv in self.conversations.values():
            if conv.user_id == user_id:
                if not active_only or conv.state == ConversationState.ACTIVE:
                    conversations.append(conv)
        
        # 按更新时间排序
        conversations.sort(key=lambda x: x.updated_at, reverse=True)
        
        return conversations
    
    def _cleanup_expired_conversations(self) -> None:
        """清理过期对话"""
        current_time = time.time()
        
        # 检查清理间隔
        if current_time - self._last_cleanup < self._cleanup_interval * 60:
            return
        
        self._last_cleanup = current_time
        
        expired_count = 0
        now = datetime.now()
        
        for conv_id, conversation in list(self.conversations.items()):
            # 检查非活跃对话的超时
            if conversation.state != ConversationState.ACTIVE:
                updated_time = datetime.fromisoformat(conversation.updated_at)
                if (now - updated_time).total_seconds() > self.session_timeout * 60:
                    del self.conversations[conv_id]
                    expired_count += 1
        
        if expired_count > 0:
            logger.info(f"清理了 {expired_count} 个过期对话")
    
    def _generate_conversation_id(self) -> str:
        """生成对话ID"""
        import uuid
        return f"conv_{uuid.uuid4().hex[:8]}"
    
    def _generate_message_id(self) -> str:
        """生成消息ID"""
        import uuid
        return f"msg_{uuid.uuid4().hex[:8]}"
    
    def _estimate_tokens(self, text: str) -> int:
        """估算token数量"""
        # 简单的估算：4个字符大约1个token
        return max(1, len(text) // 4)
    
    def _get_conversation_duration(self, conversation: Conversation) -> float:
        """获取对话持续时间"""
        try:
            start_time = datetime.fromisoformat(conversation.created_at)
            end_time = datetime.fromisoformat(conversation.updated_at)
            return (end_time - start_time).total_seconds() / 60
        except:
            return 0.0
    
    def _extract_topics(self, messages: List[Message]) -> List[str]:
        """提取对话主题"""
        # 简单的关键词提取（实际应该使用NLP技术）
        all_text = ' '.join([msg.content for msg in messages if msg.role == 'user'])
        
        # 常见问题关键词
        topic_keywords = [
            '问题', '帮助', '咨询', '如何', '为什么', '什么', '哪里', '什么时候',
            '配置', '设置', '安装', '使用', '功能', '特性', '价格', '成本',
            '支持', '文档', '指南', '教程', '示例', '错误', '故障', '解决'
        ]
        
        topics = []
        for keyword in topic_keywords:
            if keyword in all_text:
                topics.append(keyword)
                if len(topics) >= 5:  # 最多5个主题
                    break
        
        return topics
    
    def export_conversation(self, conversation_id: str, format: str = 'json') -> Optional[str]:
        """导出对话"""
        conversation = self.get_conversation(conversation_id)
        if not conversation:
            return None
        
        if format == 'json':
            return json.dumps(conversation.to_dict(), ensure_ascii=False, indent=2)
        elif format == 'text':
            return self._format_conversation_text(conversation)
        else:
            logger.warning(f"不支持的导出格式: {format}")
            return None
    
    def _format_conversation_text(self, conversation: Conversation) -> str:
        """格式化对话为文本"""
        lines = [
            f"对话ID: {conversation.conversation_id}",
            f"用户ID: {conversation.user_id}",
            f"创建时间: {conversation.created_at}",
            f"更新时间: {conversation.updated_at}",
            f"状态: {conversation.state.value}",
            "",
            "对话内容:",
            "=" * 50
        ]
        
        for message in conversation.messages:
            role_display = {
                'user': '用户',
                'assistant': '助手', 
                'system': '系统'
            }.get(message.role, message.role)
            
            time_str = datetime.fromisoformat(message.timestamp).strftime('%H:%M:%S')
            lines.append(f"\n[{time_str}] {role_display}:")
            lines.append(message.content)
        
        return '\n'.join(lines)

# 测试代码
if __name__ == "__main__":
    # 创建对话管理器
    manager = ConversationManager({
        'max_history': 10,
        'session_timeout_minutes': 60,
        'cleanup_interval_minutes': 10
    })
    
    # 测试创建对话
    print("=== 创建对话测试 ===")
    conversation = manager.create_conversation("test_user", project="demo")
    print(f"创建对话: {conversation.conversation_id}")
    
    # 测试添加消息
    print("\n=== 添加消息测试 ===")
    manager.add_message(conversation.conversation_id, "user", "你好，我想了解这个系统如何使用？")
    manager.add_message(conversation.conversation_id, "assistant", "欢迎使用！我可以帮助您了解系统的功能和使用方法。")
    manager.add_message(conversation.conversation_id, "user", "如何配置数据库连接？")
    
    # 测试获取对话
    print("\n=== 获取对话测试 ===")
    retrieved_conv = manager.get_conversation(conversation.conversation_id)
    print(f"对话消息数量: {len(retrieved_conv.messages)}")
    
    # 测试获取上下文
    print("\n=== 获取上下文测试 ===")
    context = manager.get_conversation_context(conversation.conversation_id)
    print(f"上下文消息数量: {len(context)}")
    for msg in context:
        print(f"{msg['role']}: {msg['content'][:30]}...")
    
    # 测试总结对话
    print("\n=== 对话总结测试 ===")
    summary = manager.summarize_conversation(conversation.conversation_id)
    print(f"总结: {summary}")
    
    # 测试导出
    print("\n=== 导出测试 ===")
    export_json = manager.export_conversation(conversation.conversation_id, 'json')
    print(f"JSON导出长度: {len(export_json)}")
    
    # 测试用户对话列表
    print("\n=== 用户对话列表测试 ===")
    user_conversations = manager.get_user_conversations("test_user")
    print(f"用户对话数量: {len(user_conversations)}")