import tomllib


def read_tool_version():
    # pyproject.tomlファイルのパス
    file_path = 'pyproject.toml'

    # tomlファイルを読み込む
    with open(file_path, 'rb') as toml_file:
        data = tomllib.load(toml_file)

    # バージョン情報を取得
    return data['tool']['poetry']['version']


# バージョン情報を取得
tool_version = read_tool_version()
