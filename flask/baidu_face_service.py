from aip import AipFace
import base64
import json
from config import Config


class BaiduFaceService:
    def __init__(self):
        self.client = AipFace(Config.BAIDU_APP_ID, Config.BAIDU_API_KEY, Config.BAIDU_SECRET_KEY)
        self.group_id = Config.BAIDU_GROUP_ID

    def get_image_base64(self, image_path):
        """将图片转换为base64编码"""
        with open(image_path, 'rb') as f:
            return base64.b64encode(f.read()).decode('utf-8')

    def add_face(self, image_path, user_id, user_info):
        """
        添加人脸到百度人脸库
        """
        try:
            # 读取图片并转换为base64
            image_base64 = self.get_image_base64(image_path)

            # 调用百度人脸注册接口
            result = self.client.addUser(
                image_base64,
                "BASE64",
                self.group_id,
                user_id,
                {
                    "user_info": user_info,
                    "quality_control": "NORMAL",  # 质量控制
                    "liveness_control": "NORMAL"  # 活体控制
                }
            )

            print(f"百度人脸注册结果: {result}")
            return result

        except Exception as e:
            print(f"添加人脸到百度AI失败: {str(e)}")
            return None

    def search_face(self, image_path):
        """
        在百度人脸库中搜索人脸
        """
        try:
            # 读取图片并转换为base64
            image_base64 = self.get_image_base64(image_path)

            # 调用百度人脸搜索接口
            result = self.client.search(
                image_base64,
                "BASE64",
                self.group_id,
                {
                    "quality_control": "NORMAL",
                    "liveness_control": "NORMAL",
                    "max_user_num": 1  # 返回最相似的1个结果
                }
            )

            print(f"百度人脸搜索结果: {result}")
            return result

        except Exception as e:
            print(f"在百度AI搜索人脸失败: {str(e)}")
            return None

    def create_group(self):
        """创建人脸库分组"""
        try:
            result = self.client.groupAdd(self.group_id)
            return result
        except Exception as e:
            print(f"创建人脸库分组失败: {str(e)}")
            return None

    def delete_face(self, user_id):
        """删除人脸"""
        try:
            result = self.client.deleteUser(self.group_id, user_id)
            return result
        except Exception as e:
            print(f"删除人脸失败: {str(e)}")
            return None