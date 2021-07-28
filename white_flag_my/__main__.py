from dotenv import load_dotenv

from . import lambda_function

if __name__ == "__main__":

    load_dotenv("./.env")
    _ = lambda_function.lambda_handler("", "")
