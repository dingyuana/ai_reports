#!/usr/bin/env python3
"""
测试Docker容器中的LibreOffice是否正常工作
"""

import os
import subprocess
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_libreoffice_availability():
    """测试LibreOffice是否可在系统中使用"""
    try:
        # 检查libreoffice命令是否可用
        result = subprocess.run(
            ["libreoffice", "--version"],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            logger.info(f"LibreOffice可用，版本信息: {result.stdout.strip()}")
            return True
        else:
            logger.error(f"LibreOffice不可用: {result.stderr.strip()}")
            return False
            
    except Exception as e:
        logger.error(f"检查LibreOffice时出错: {e}", exc_info=True)
        return False

if __name__ == "__main__":
    test_libreoffice_availability()
