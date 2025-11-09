import logging
import os
from datetime import datetime
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path
from threading import RLock


class Logger:
    """Cache per-module loggers; each name gets its own logger object."""

    _loggers: dict[str, logging.Logger] = {}
    _logs_dir: Path | None = None
    _lock = RLock()

    @classmethod
    def _resolve_logs_dir(cls) -> Path:
        if cls._logs_dir is not None:
            return cls._logs_dir

        env_log_dir = os.getenv("LOG_DIR")
        if env_log_dir:
            logs_dir = Path(env_log_dir).expanduser().resolve()
        else:
            current_file = Path(__file__).resolve()
            project_root = current_file.parents[2] if (current_file.parents[2] / "src").is_dir() else Path.cwd()
            logs_dir = project_root / "logs"

        logs_dir.mkdir(parents=True, exist_ok=True)
        cls._logs_dir = logs_dir
        return logs_dir

    @classmethod
    def get_logger(cls, name: str, level: int = logging.INFO) -> logging.Logger:
        with cls._lock:
            if name in cls._loggers:
                return cls._loggers[name]

            logger = logging.getLogger(name)
            logger.setLevel(level)
            logger.propagate = False

            if not logger.handlers:
                formatter = logging.Formatter(
                    fmt="%(asctime)s [%(levelname)s] %(filename)s:%(lineno)d %(message)s",
                    datefmt="%Y-%m-%d %H:%M:%S",
                )

                logs_dir = cls._resolve_logs_dir()

                base_filename = f'app_{datetime.now().strftime("%Y-%m-%d")}.log'
                file_path = logs_dir / base_filename

                fh = TimedRotatingFileHandler(
                    filename=str(file_path),
                    when="midnight",
                    interval=1,
                    backupCount=7,
                    encoding="utf-8",
                    utc=False,
                )
                fh.setLevel(level)
                fh.setFormatter(formatter)
                logger.addHandler(fh)

                ch = logging.StreamHandler()
                console_level_name = os.getenv("LOG_CONSOLE_LEVEL", "INFO").upper()
                ch.setLevel(getattr(logging, console_level_name, logging.INFO))
                ch.setFormatter(formatter)
                logger.addHandler(ch)

                logger.debug(f"Logger initialized. Writing to: {file_path}")

            cls._loggers[name] = logger
            return logger
