"""Utility functions."""
from typing import Optional, List


def read_last_log_lines(log_path: Optional[str], num_lines: int = 20) -> str:
    """
    Read the last N lines from a log file.
    
    Args:
        log_path: Path to the log file
        num_lines: Number of lines to read
    
    Returns:
        Last N lines of the log file
    """
    if not log_path:
        return ""
    
    try:
        with open(log_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
            return ''.join(lines[-num_lines:])
    except FileNotFoundError:
        return "Log file not found"
    except Exception as e:
        return f"Error reading log file: {e}"


def filter_logs_by_user(log_path: Optional[str], user_id: int, max_lines: int = 50) -> str:
    """
    Filter log lines that contain specific user ID.
    
    Args:
        log_path: Path to the log file
        user_id: User ID to filter by
        max_lines: Maximum number of lines to return
    
    Returns:
        Filtered log lines containing the user ID
    """
    if not log_path:
        return ""
    
    try:
        with open(log_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
            
        # Filter lines containing the user ID
        user_lines = []
        for line in lines:
            if str(user_id) in line:
                user_lines.append(line)
        
        # Return last N lines if too many
        if len(user_lines) > max_lines:
            user_lines = user_lines[-max_lines:]
        
        return ''.join(user_lines)
        
    except FileNotFoundError:
        return "Log file not found"
    except Exception as e:
        return f"Error reading log file: {e}"


def get_user_activity_summary(log_path: Optional[str], user_id: int) -> dict:
    """
    Get summary of user activity from logs.
    
    Args:
        log_path: Path to the log file
        user_id: User ID to analyze
    
    Returns:
        Dictionary with activity summary
    """
    if not log_path:
        return {"error": "No log path provided"}
    
    try:
        with open(log_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        
        user_lines = [line for line in lines if str(user_id) in line]
        
        if not user_lines:
            return {"error": f"No logs found for user {user_id}"}
        
        # Count different activities
        activities = {
            "start": 0,
            "balance": 0,
            "logs": 0,
            "users": 0,
            "unknown": 0
        }
        
        for line in user_lines:
            if "START!" in line:
                activities["start"] += 1
            elif "Проверить баланс" in line:
                activities["balance"] += 1
            elif "Show logs" in line:
                activities["logs"] += 1
            elif "Show users" in line:
                activities["users"] += 1
            elif "Unknown command" in line:
                activities["unknown"] += 1
        
        return {
            "total_entries": len(user_lines),
            "activities": activities,
            "last_activity": user_lines[-1].strip() if user_lines else None
        }
        
    except Exception as e:
        return {"error": f"Error analyzing logs: {e}"}

