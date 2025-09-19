"""
Health check utilities for the grading system
"""
import os
import time
import psutil
import logging
from typing import Dict, Any, List
from datetime import datetime, timedelta
import requests
from config import ARK_API_KEY, API_CONFIG, TEMP_DIR, LOGS_DIR, REPORTS_DIR, OUTPUT_DIR

logger = logging.getLogger(__name__)

class HealthChecker:
    """System health checker"""
    
    def __init__(self):
        self.start_time = time.time()
        self.last_check_time = None
        self.check_history: List[Dict[str, Any]] = []
        self.max_history = 100
    
    def check_system_health(self) -> Dict[str, Any]:
        """
        Perform comprehensive system health check
        
        Returns:
            Dictionary containing health status and details
        """
        health_status = {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "uptime_seconds": time.time() - self.start_time,
            "checks": {}
        }
        
        # Individual health checks
        checks = [
            ("disk_space", self._check_disk_space),
            ("memory_usage", self._check_memory_usage),
            ("cpu_usage", self._check_cpu_usage),
            ("directories", self._check_directories),
            ("ai_service", self._check_ai_service),
            ("temp_files", self._check_temp_files),
            ("log_files", self._check_log_files)
        ]
        
        overall_healthy = True
        
        for check_name, check_func in checks:
            try:
                check_result = check_func()
                health_status["checks"][check_name] = check_result
                
                if not check_result.get("healthy", True):
                    overall_healthy = False
                    
            except Exception as e:
                logger.error(f"Health check '{check_name}' failed: {e}")
                health_status["checks"][check_name] = {
                    "healthy": False,
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                }
                overall_healthy = False
        
        # Set overall status
        health_status["status"] = "healthy" if overall_healthy else "unhealthy"
        
        # Store in history
        self._store_check_result(health_status)
        
        return health_status
    
    def _check_disk_space(self) -> Dict[str, Any]:
        """Check available disk space"""
        try:
            # Check disk usage for important directories
            directories_to_check = [
                ("/app", "Application directory"),
                (TEMP_DIR, "Temporary files"),
                (LOGS_DIR, "Log files"),
                (REPORTS_DIR, "Student reports"),
                (OUTPUT_DIR, "Output files")
            ]
            
            disk_info = {}
            overall_healthy = True
            
            for dir_path, description in directories_to_check:
                if os.path.exists(dir_path):
                    usage = psutil.disk_usage(dir_path)
                    free_percent = (usage.free / usage.total) * 100
                    
                    disk_info[dir_path] = {
                        "description": description,
                        "total_gb": round(usage.total / (1024**3), 2),
                        "used_gb": round(usage.used / (1024**3), 2),
                        "free_gb": round(usage.free / (1024**3), 2),
                        "free_percent": round(free_percent, 2),
                        "healthy": free_percent > 10  # Alert if less than 10% free
                    }
                    
                    if free_percent <= 10:
                        overall_healthy = False
            
            return {
                "healthy": overall_healthy,
                "disk_usage": disk_info,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                "healthy": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def _check_memory_usage(self) -> Dict[str, Any]:
        """Check memory usage"""
        try:
            memory = psutil.virtual_memory()
            swap = psutil.swap_memory()
            
            memory_healthy = memory.percent < 90  # Alert if memory usage > 90%
            swap_healthy = swap.percent < 50 if swap.total > 0 else True
            
            return {
                "healthy": memory_healthy and swap_healthy,
                "memory": {
                    "total_gb": round(memory.total / (1024**3), 2),
                    "used_gb": round(memory.used / (1024**3), 2),
                    "free_gb": round(memory.free / (1024**3), 2),
                    "percent_used": memory.percent,
                    "healthy": memory_healthy
                },
                "swap": {
                    "total_gb": round(swap.total / (1024**3), 2),
                    "used_gb": round(swap.used / (1024**3), 2),
                    "percent_used": swap.percent,
                    "healthy": swap_healthy
                } if swap.total > 0 else None,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                "healthy": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def _check_cpu_usage(self) -> Dict[str, Any]:
        """Check CPU usage"""
        try:
            # Get CPU usage over a short interval
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_count = psutil.cpu_count()
            load_avg = os.getloadavg() if hasattr(os, 'getloadavg') else None
            
            cpu_healthy = cpu_percent < 80  # Alert if CPU usage > 80%
            
            result = {
                "healthy": cpu_healthy,
                "cpu_percent": cpu_percent,
                "cpu_count": cpu_count,
                "timestamp": datetime.now().isoformat()
            }
            
            if load_avg:
                result["load_average"] = {
                    "1min": load_avg[0],
                    "5min": load_avg[1],
                    "15min": load_avg[2]
                }
            
            return result
            
        except Exception as e:
            return {
                "healthy": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def _check_directories(self) -> Dict[str, Any]:
        """Check if required directories exist and are writable"""
        try:
            directories = [
                (REPORTS_DIR, "Student reports directory"),
                (OUTPUT_DIR, "Output directory"),
                (TEMP_DIR, "Temporary files directory"),
                (LOGS_DIR, "Logs directory")
            ]
            
            dir_status = {}
            overall_healthy = True
            
            for dir_path, description in directories:
                exists = os.path.exists(dir_path)
                writable = os.access(dir_path, os.W_OK) if exists else False
                readable = os.access(dir_path, os.R_OK) if exists else False
                
                dir_healthy = exists and writable and readable
                
                dir_status[dir_path] = {
                    "description": description,
                    "exists": exists,
                    "writable": writable,
                    "readable": readable,
                    "healthy": dir_healthy
                }
                
                if not dir_healthy:
                    overall_healthy = False
            
            return {
                "healthy": overall_healthy,
                "directories": dir_status,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                "healthy": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def _check_ai_service(self) -> Dict[str, Any]:
        """Check AI service connectivity"""
        try:
            # Test ARK API connectivity
            from volcenginesdkarkruntime import Ark
            
            ark = Ark(api_key=ARK_API_KEY)
            
            # Simple test call with timeout
            start_time = time.time()
            try:
                # Use a minimal test prompt
                completion = ark.chat.completions.create(
                    model="doubao-1-5-thinking-pro-250415",
                    messages=[{"role": "user", "content": "test"}],
                    max_tokens=1,
                    timeout=10
                )
                response_time = time.time() - start_time
                
                return {
                    "healthy": True,
                    "service": "ARK API",
                    "response_time_seconds": round(response_time, 2),
                    "status": "connected",
                    "timestamp": datetime.now().isoformat()
                }
                
            except Exception as api_error:
                return {
                    "healthy": False,
                    "service": "ARK API",
                    "error": str(api_error),
                    "status": "connection_failed",
                    "timestamp": datetime.now().isoformat()
                }
                
        except Exception as e:
            return {
                "healthy": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def _check_temp_files(self) -> Dict[str, Any]:
        """Check temporary files status"""
        try:
            from utils.temp_file_manager import temp_manager
            
            usage = temp_manager.get_temp_usage()
            
            # Consider unhealthy if temp usage is too high
            temp_healthy = usage["total_size_mb"] < 1000  # Alert if > 1GB
            
            return {
                "healthy": temp_healthy,
                "usage": usage,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                "healthy": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def _check_log_files(self) -> Dict[str, Any]:
        """Check log files status"""
        try:
            log_info = {}
            overall_healthy = True
            
            if os.path.exists(LOGS_DIR):
                total_log_size = 0
                log_count = 0
                
                for root, dirs, files in os.walk(LOGS_DIR):
                    for file in files:
                        if file.endswith('.log'):
                            file_path = os.path.join(root, file)
                            try:
                                size = os.path.getsize(file_path)
                                total_log_size += size
                                log_count += 1
                            except Exception:
                                pass
                
                total_log_size_mb = total_log_size / (1024 * 1024)
                
                # Alert if log files are too large
                logs_healthy = total_log_size_mb < 500  # Alert if > 500MB
                
                log_info = {
                    "total_size_mb": round(total_log_size_mb, 2),
                    "file_count": log_count,
                    "healthy": logs_healthy
                }
                
                if not logs_healthy:
                    overall_healthy = False
            
            return {
                "healthy": overall_healthy,
                "logs": log_info,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                "healthy": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def _store_check_result(self, result: Dict[str, Any]):
        """Store health check result in history"""
        self.check_history.append(result)
        
        # Keep only the last N results
        if len(self.check_history) > self.max_history:
            self.check_history = self.check_history[-self.max_history:]
        
        self.last_check_time = time.time()
    
    def get_health_summary(self) -> Dict[str, Any]:
        """Get a summary of recent health checks"""
        if not self.check_history:
            return {"message": "No health checks performed yet"}
        
        recent_checks = self.check_history[-10:]  # Last 10 checks
        healthy_count = sum(1 for check in recent_checks if check["status"] == "healthy")
        
        return {
            "recent_checks_count": len(recent_checks),
            "healthy_checks": healthy_count,
            "unhealthy_checks": len(recent_checks) - healthy_count,
            "health_rate": round((healthy_count / len(recent_checks)) * 100, 2),
            "last_check": recent_checks[-1] if recent_checks else None,
            "uptime_seconds": time.time() - self.start_time
        }

# Global health checker instance
health_checker = HealthChecker()