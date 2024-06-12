# run.py
import sys
from app import create_app
from config import DevelopmentConfig, TestingConfig, ProductionConfig


def main():
    env = "dev"
    if len(sys.argv) == 2:
        env = sys.argv[1].split("=")[-1]

    print(f"Running in {env} environment")
    if env == "dev":
        target_config = DevelopmentConfig
    elif env == "test":
        target_config = TestingConfig
    elif env == "prod":
        target_config = ProductionConfig
    else:
        print("Invalid environment. Use one of: dev, test, prod")
        return

    app = create_app(target_config)
    app.run(host='0.0.0.0', port=target_config.PORT, debug=target_config.DEBUG)


if __name__ == '__main__':
    main()
