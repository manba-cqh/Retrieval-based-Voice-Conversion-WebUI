"""异步工具函数，用于在PyQt6中执行异步操作"""
import asyncio
from typing import Coroutine, Any
from PyQt6.QtCore import QThread, pyqtSignal, QObject


class AsyncWorker(QObject):
    """异步工作线程"""
    finished = pyqtSignal(object)  # 发送结果
    error = pyqtSignal(str)  # 发送错误信息
    
    def __init__(self, coro: Coroutine):
        """
        初始化异步工作线程
        
        Args:
            coro: 异步协程对象
        """
        super().__init__()
        self.coro = coro
    
    def run(self):
        """在线程中运行异步协程"""
        try:
            # 创建新的事件循环
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # 运行协程
            result = loop.run_until_complete(self.coro)
            
            # 发送结果
            self.finished.emit(result)
            
            # 关闭事件循环
            loop.close()
        except Exception as e:
            self.error.emit(str(e))


def run_async(coro: Coroutine) -> tuple[QThread, AsyncWorker]:
    """
    在单独的线程中运行异步协程
    
    Args:
        coro: 异步协程对象
    
    Returns:
        (thread, worker) 元组，thread是QThread实例，worker是AsyncWorker实例
    """
    worker = AsyncWorker(coro)
    thread = QThread()
    worker.moveToThread(thread)
    
    # 连接信号
    thread.started.connect(worker.run)
    thread.finished.connect(thread.deleteLater)
    
    return thread, worker


class AsyncTaskManager:
    """异步任务管理器，用于管理多个异步任务"""
    
    def __init__(self):
        self.tasks: dict[str, tuple[QThread, AsyncWorker]] = {}
    
    def run_task(self, task_id: str, coro: Coroutine) -> tuple[QThread, AsyncWorker]:
        """
        运行异步任务
        
        Args:
            task_id: 任务ID
            coro: 异步协程对象
        
        Returns:
            (thread, worker) 元组
        """
        # 如果任务已存在，先停止
        if task_id in self.tasks:
            self.cancel_task(task_id)
        
        thread, worker = run_async(coro)
        self.tasks[task_id] = (thread, worker)
        
        # 任务完成后自动清理
        thread.finished.connect(lambda: self._cleanup_task(task_id))
        
        return thread, worker
    
    def cancel_task(self, task_id: str):
        """取消任务"""
        if task_id in self.tasks:
            thread, worker = self.tasks[task_id]
            try:
                if thread.isRunning():
                    thread.terminate()
                    thread.wait(1000)  # 等待最多1秒
            except RuntimeError:
                pass
            
            try:
                if thread:
                    thread.deleteLater()
            except RuntimeError:
                pass
            
            try:
                if worker:
                    worker.deleteLater()
            except RuntimeError:
                pass
            
            if task_id in self.tasks:
                del self.tasks[task_id]
    
    def _cleanup_task(self, task_id: str):
        """清理任务"""
        if task_id in self.tasks:
            thread, worker = self.tasks[task_id]
            try:
                if thread:
                    thread.deleteLater()
            except RuntimeError:
                pass
            
            try:
                if worker:
                    worker.deleteLater()
            except RuntimeError:
                pass
            
            if task_id in self.tasks:
                del self.tasks[task_id]
    
    def cancel_all(self):
        """取消所有任务"""
        task_ids = list(self.tasks.keys())
        for task_id in task_ids:
            self.cancel_task(task_id)

