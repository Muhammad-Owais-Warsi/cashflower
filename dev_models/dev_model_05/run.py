import sys
from cashflower import start
from settings import settings


if __name__ == "__main__":
    output, timestamp = start("dev_model_05", settings, sys.argv)