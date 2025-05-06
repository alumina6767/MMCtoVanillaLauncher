
import os
import shutil
import zipfile
import json
import base64
from portablemc.fabric import FabricVersion
from portablemc.forge import ForgeVersion, _NeoForgeVersion

from portablemc.standard import Version
import portablemc.standard

# MMCのzipの置き場
MMC_DIR = 'MMC'

# 仮のファイル置き場
PROFILES_DIR = 'profiles'

# 起動構成のZIP名
mmc_zip = 'MMC\\1.21.4_Fabric_kuronekotemp_20250218_MMC2.zip'

# MMCの設定ファイル
MMC_PACK = 'mmc-pack.json'

# ランチャーの設定ファイル
LAUNCHER_PROFILES = os.path.join(
    portablemc.standard.get_minecraft_dir(), 'launcher_profiles.json')


def get_config(data):
    """
    MMCの設定ファイルから、Minecraftのver、loader(Forge/Fabric/NeoForge)の名前、loaderのverを取得する

    Args:
        data (dict):MMCの設定ファイル

    Returns:
        dict:Minecraftのver、loaderの名前、loaderのver
    """

    version = 'latest'
    loader = None
    loader_version = None

    for component in data['components']:

        # verの取得
        if component['cachedName'] == 'Minecraft':
            version = component['version']

        # loaderの取得
        elif component['cachedName'] == 'Fabric Loader':
            loader = 'fabric'
            loader_version = component['version']

        elif component['cachedName'] == 'NeoForge':
            loader = 'neoforge'
            loader_version = component['version']

        elif component['cachedName'] == 'Forge':
            loader = 'forge'
            loader_version = component['version']

    config = {'version': version, 'loader': loader,
              'loader_version': loader_version}
    return config


def image_file_to_base64(file_path):
    """
    画像ファイルをbase64文字列に変換

    Args:
        file_path (str): 画像ファイルのパス

    Returns:
        str: base64文字列
    """

    with open(file_path, "rb") as image_file:
        data = base64.b64encode(image_file.read())

    return data.decode('utf-8')

def unzip_file(zip_path, extract_dir_path):

    """
    ZIPファイルを展開

    Args:
        zip_path (str): ZIPファイルのパス
        extract_dir_path (str): 展開先のディレクトリ
    """
    
    # マルチMCから書き出されたZIPは文字化けする
    with zipfile.ZipFile(zip_path) as z:
        for info in z.infolist():
            print(info)
            info.filename = info.orig_filename.encode('cp437').decode('cp932')
            if os.sep != "/" and os.sep in info.filename:
                info.filename = info.filename.replace(os.sep, "/")
            z.extract(info, extract_dir_path)


if __name__ == '__main__':
    try:
        for mmc_zip in os.listdir(MMC_DIR):
            if not mmc_zip.endswith('.zip'):
                continue

            # 通知
            print(f'\n起動構成 {mmc_zip} をインストールします。')

            # 起動構成の名前
            mmc_name = os.path.splitext(os.path.basename(mmc_zip))[0]
            profile_dir = os.path.join(os.getcwd(), PROFILES_DIR, mmc_name)
            game_dir = os.path.join(profile_dir, '.minecraft')

            # 仮のファイル置き場を作成
            if not os.path.exists(PROFILES_DIR):
                os.mkdir(PROFILES_DIR)

            # ZIPを解凍
            mmc_zip_path = os.path.join(MMC_DIR, mmc_zip)
            shutil.unpack_archive(mmc_zip_path, profile_dir)

            # ZIPからverなどを読み込み
            mmc_pack_path = os.path.join(profile_dir, MMC_PACK)
            
            # 設定ファイル読み込み失敗時
            if not os.path.exists(mmc_pack_path):

                # 解凍し直す            
                shutil.rmtree(profile_dir)
                unzip_file(mmc_zip_path, profile_dir)

                # ZIPが2重になっている時
                duplicate_dir = os.path.join(profile_dir, mmc_name)
                if os.path.exists(duplicate_dir):
                    os.renames(duplicate_dir, profile_dir+'_new')
                    os.renames(profile_dir+'_new', profile_dir)
            
                else:
                    print("MMCの設定ファイルを読み込めませんでした。")
                    continue
                
            with open(os.path.join(profile_dir, MMC_PACK), 'r') as f:
                mmc_pack = json.load(f)
                config = get_config(mmc_pack)

            # ローダーのインストール
            if config['loader'] == 'fabric':
                print(f'fabric-{config["version"]}-{config["loader_version"]} をインストールします。')
                version = FabricVersion.with_fabric(vanilla_version=config['version'], loader_version=config['loader_version'])
                version.install()
                last_version_id = f'fabric-{config["version"]}-{config["loader_version"]}'

            elif config['loader'] == 'neoforge':
                print(f'neoforge-{config["loader_version"]} をインストールします。')
                version = _NeoForgeVersion(f"{config['loader_version']}")
                version.install()
                last_version_id = f'neoforge-{config["loader_version"]}'

            elif config['loader'] == 'forge':
                print(f'forge-{config["version"]}-{config["loader_version"]} をインストールします。')
                version = ForgeVersion(f"{config['version']}-{config['loader_version']}")
                version.install()
                last_version_id = f'forge-{config["version"]}-{config["loader_version"]}'

            # ローダーが不明だった時
            else:
                print(f'vanilla-{config["version"]} をインストールします。')
                version = Version(config['version'])
                version.install()
                last_version_id = f'{config["version"]}'

            # 起動構成の読み込み
            with open(LAUNCHER_PROFILES, 'r') as f:
                launcher_profile = json.load(f)

            # 既に存在する場合
            if mmc_zip in launcher_profile['profiles']:
                print('既に同名の起動構成が存在します。')
                continue

            # アイコン
            icon_path = os.path.join(game_dir, 'icon.png')
            if os.path.exists(icon_path):
                icon = f"data:image/png;base64,{image_file_to_base64(icon_path)}"

            else:
                icon = "Grass"

            # 起動構成の追加
            launcher_profile['profiles'][mmc_zip] = {
                "gameDir": game_dir,
                "icon": icon,
                "lastVersionId": last_version_id,
                "name": mmc_name,
                "type": "custom"
            }

            with open(LAUNCHER_PROFILES, 'w') as f:
                json.dump(launcher_profile, f, indent=4)

            print("インストールが完了しました。")

        print('\n全ての起動構成のインストールを完了しました。\nマイクラのランチャーを再起動してください。\nエンターキーで終了します。')
        input()
    
    except Exception as e:
        print(e)
        print('\nエラーが発生しました。\nエンターキーで終了します。')
        input()
