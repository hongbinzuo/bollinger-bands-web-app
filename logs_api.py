from flask import Blueprint, request, jsonify
import logging
import os
from datetime import datetime
import json

logger = logging.getLogger(__name__)

# 创建蓝图
logs_bp = Blueprint('logs', __name__, url_prefix='/logs')

# 内存日志存储
memory_logs = []
MAX_MEMORY_LOGS = 1000

class WebLogHandler(logging.Handler):
    """自定义日志处理器，将日志存储到内存中"""
    
    def emit(self, record):
        try:
            log_entry = {
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3],
                'level': record.levelname,
                'message': record.getMessage(),
                'module': record.module,
                'funcName': record.funcName,
                'lineno': record.lineno
            }
            
            # 添加到内存日志
            memory_logs.append(log_entry)
            
            # 限制内存日志数量
            if len(memory_logs) > MAX_MEMORY_LOGS:
                memory_logs.pop(0)
                
        except Exception as e:
            print(f"日志处理器错误: {e}")

# 添加自定义日志处理器
web_handler = WebLogHandler()
web_handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
web_handler.setFormatter(formatter)

# 获取根日志记录器并添加处理器
root_logger = logging.getLogger()
root_logger.addHandler(web_handler)

@logs_bp.route('/get_logs', methods=['GET'])
def get_logs():
    """获取内存中的日志"""
    try:
        level_filter = request.args.get('level', 'all')
        search_term = request.args.get('search', '')
        limit = int(request.args.get('limit', 100))
        
        # 过滤日志
        filtered_logs = memory_logs.copy()
        
        # 按级别过滤
        if level_filter != 'all':
            filtered_logs = [log for log in filtered_logs if log['level'] == level_filter]
        
        # 按关键词搜索
        if search_term:
            filtered_logs = [log for log in filtered_logs 
                           if search_term.lower() in log['message'].lower()]
        
        # 限制数量
        filtered_logs = filtered_logs[-limit:]
        
        return jsonify({
            'success': True,
            'logs': filtered_logs,
            'total': len(filtered_logs),
            'memory_total': len(memory_logs)
        })
        
    except Exception as e:
        logger.error(f"获取日志失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        })

@logs_bp.route('/clear_logs', methods=['POST'])
def clear_logs():
    """清空内存日志"""
    try:
        global memory_logs
        memory_logs.clear()
        
        # 添加清空日志记录
        logger.info("内存日志已清空")
        
        return jsonify({
            'success': True,
            'message': '日志已清空'
        })
        
    except Exception as e:
        logger.error(f"清空日志失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        })

@logs_bp.route('/export_logs', methods=['GET'])
def export_logs():
    """导出日志"""
    try:
        level_filter = request.args.get('level', 'all')
        search_term = request.args.get('search', '')
        
        # 过滤日志
        filtered_logs = memory_logs.copy()
        
        if level_filter != 'all':
            filtered_logs = [log for log in filtered_logs if log['level'] == level_filter]
        
        if search_term:
            filtered_logs = [log for log in filtered_logs 
                           if search_term.lower() in log['message'].lower()]
        
        # 生成导出内容
        export_content = []
        for log in filtered_logs:
            export_content.append(
                f"[{log['timestamp']}] {log['level']} - {log['message']}"
            )
        
        return jsonify({
            'success': True,
            'content': '\n'.join(export_content),
            'count': len(export_content)
        })
        
    except Exception as e:
        logger.error(f"导出日志失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        })

@logs_bp.route('/test_logs', methods=['POST'])
def test_logs():
    """测试日志功能"""
    try:
        data = request.get_json()
        test_message = data.get('message', '测试日志消息')
        
        # 生成不同级别的测试日志
        logger.info(f"测试INFO日志: {test_message}")
        logger.warning(f"测试WARNING日志: {test_message}")
        logger.error(f"测试ERROR日志: {test_message}")
        
        return jsonify({
            'success': True,
            'message': '测试日志已生成'
        })
        
    except Exception as e:
        logger.error(f"测试日志失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        })
