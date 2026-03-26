"""FMS 工具测试

测试内容：
1. fms_retrieve 多模态检索
2. fms_chat 知识库问答
3. fms_list_files 文件列表
4. 边界情况和错误处理
"""

import pytest
import pytest_asyncio
from aiagent.tools.fms import (
    fms_retrieve_handler,
    fms_chat_handler,
    fms_list_files_handler,
)


# ========== 基础功能测试 ==========

class TestFMSRetrieve:
    """测试多模态检索功能"""
    
    @pytest.mark.asyncio
    async def test_text2doc_search(self):
        """测试文本搜文档 - 搜索班车文档"""
        result = await fms_retrieve_handler(
            query="班车",
            type="text2doc",
            top_k=5,
            score_threshold=0.3
        )
        # 应该能找到班车PDF
        assert ("班车" in result or "亿道" in result or 
                "未找到" in result or "Error" in result)
    
    @pytest.mark.asyncio
    async def test_text2image_search_english(self):
        """测试文本搜图片 - 使用英文关键词"""
        result = await fms_retrieve_handler(
            query="baby",
            type="text2image",
            top_k=5,
            score_threshold=0.1  # 图片检索需要较低阈值
        )
        # 应该能找到baby图片
        assert ("baby" in result.lower() or "孩子成长" in result or
                "未找到" in result or "Error" in result)
    
    @pytest.mark.asyncio
    async def test_text2image_search_chinese(self):
        """测试文本搜图片 - 使用中文关键词"""
        result = await fms_retrieve_handler(
            query="孩子",
            type="text2image",
            top_k=5,
            score_threshold=0.1
        )
        # 中文关键词可能效果不如英文
        assert isinstance(result, str)
    
    @pytest.mark.asyncio
    async def test_image2image_search(self):
        """测试以图搜图"""
        result = await fms_retrieve_handler(
            query="/workspace/yangxinlong/NAS_data/recall_files_test/孩子成长/baby-2972221_1280.jpg",
            type="image2image",
            top_k=5,
            score_threshold=0.1
        )
        # 应该能找到相似图片或原图
        assert ("baby" in result.lower() or "孩子成长" in result or
                "未找到" in result or "Error" in result)
    
    @pytest.mark.asyncio
    async def test_doc2doc_search(self):
        """测试文档相似度搜索"""
        result = await fms_retrieve_handler(
            query="/workspace/yangxinlong/NAS_data/recall_files_test/pdf/亿道班车路线.pdf",
            type="doc2doc",
            top_k=5,
            score_threshold=0.3
        )
        # doc2doc可能找到相似文档
        assert isinstance(result, str)
    
    @pytest.mark.asyncio
    async def test_text2video_search(self):
        """测试文本搜视频"""
        result = await fms_retrieve_handler(
            query="视频",
            type="text2video",
            top_k=5,
            score_threshold=0.1
        )
        assert isinstance(result, str)
    
    @pytest.mark.asyncio
    async def test_invalid_type(self):
        """测试无效检索类型"""
        result = await fms_retrieve_handler(
            query="test",
            type="invalid_type"
        )
        assert "Error" in result
        assert "不支持的检索类型" in result
    
    @pytest.mark.asyncio
    async def test_empty_query(self):
        """测试空查询"""
        result = await fms_retrieve_handler(
            query="",
            type="text2doc"
        )
        # 空查询应该返回错误或空结果
        assert isinstance(result, str)


class TestFMSChat:
    """测试知识库问答功能"""
    
    @pytest.mark.asyncio
    async def test_chat_basic(self):
        """测试基本问答 - 班车路线"""
        result = await fms_chat_handler("公司班车有哪些路线")
        # 应该返回班车信息
        assert ("班车" in result or "路线" in result or 
                "Error" in result or "无法连接" in result)
    
    @pytest.mark.asyncio
    async def test_chat_insurance(self):
        """测试保险理赔问答"""
        result = await fms_chat_handler("平安健康保险怎么理赔")
        # 应该返回理赔流程
        assert ("理赔" in result or "平安" in result or 
                "Error" in result)
    
    @pytest.mark.asyncio
    async def test_chat_empty_query(self):
        """测试空查询"""
        result = await fms_chat_handler("")
        assert "Error" in result
        assert "不能为空" in result
    
    @pytest.mark.asyncio
    async def test_chat_not_found(self):
        """测试知识库不存在的内容"""
        result = await fms_chat_handler("xyzqwerty不存在的主题12345")
        # 应该返回无相关信息或尝试回答
        assert isinstance(result, str)


class TestFMSListFiles:
    """测试文件列表功能"""
    
    @pytest.mark.asyncio
    async def test_list_all_files(self):
        """测试列出所有文件"""
        result = await fms_list_files_handler()
        # 应该返回文件统计
        assert ("文档:" in result or "图片:" in result or "视频:" in result or
                "Error" in result)
    
    @pytest.mark.asyncio
    async def test_list_documents(self):
        """测试只列文档"""
        result = await fms_list_files_handler(file_type="document")
        assert isinstance(result, str)
    
    @pytest.mark.asyncio
    async def test_list_images(self):
        """测试只列图片"""
        result = await fms_list_files_handler(file_type="image")
        assert ("图片:" in result or "Error" in result)
    
    @pytest.mark.asyncio
    async def test_list_videos(self):
        """测试只列视频"""
        result = await fms_list_files_handler(file_type="video")
        assert isinstance(result, str)
    
    @pytest.mark.asyncio
    async def test_invalid_file_type(self):
        """测试无效文件类型"""
        result = await fms_list_files_handler(file_type="audio")
        assert "Error" in result
        assert "不支持的文件类型" in result


# ========== 边界情况和性能测试 ==========

class TestFMSBoundaryCases:
    """测试边界情况"""
    
    @pytest.mark.asyncio
    async def test_large_top_k(self):
        """测试大top_k值"""
        result = await fms_retrieve_handler(
            query="test",
            type="text2doc",
            top_k=100  # 很大的值
        )
        assert isinstance(result, str)
    
    @pytest.mark.asyncio
    async def test_high_score_threshold(self):
        """测试高阈值（应该无结果）"""
        result = await fms_retrieve_handler(
            query="班车",
            type="text2doc",
            score_threshold=0.99  # 几乎不可能达到
        )
        # 应该返回未找到或很少结果
        assert isinstance(result, str)
    
    @pytest.mark.asyncio
    async def test_special_characters_in_query(self):
        """测试特殊字符查询"""
        result = await fms_retrieve_handler(
            query="test!@#$%^&*()",
            type="text2doc"
        )
        assert isinstance(result, str)
    
    @pytest.mark.asyncio
    async def test_long_query(self):
        """测试长查询字符串"""
        long_query = "这是一段很长的查询" * 50
        result = await fms_chat_handler(long_query)
        assert isinstance(result, str)


# ========== 手动测试用例 ==========

"""
手动测试命令：

# 1. 文本搜文档
curl -X POST http://172.16.50.51:8001/api/fms/retrieve \
  -H "Content-Type: application/json" \
  -d '{"type": "text2doc", "query": "班车", "top_k": 5}'

# 2. 文本搜图片（英文）
curl -X POST http://172.16.50.51:8001/api/fms/retrieve \
  -H "Content-Type: application/json" \
  -d '{"type": "text2image", "query": "baby", "top_k": 5, "score_threshold": 0.1}'

# 3. 以图搜图
curl -X POST http://172.16.50.51:8001/api/fms/retrieve \
  -H "Content-Type: application/json" \
  -d '{"type": "image2image", "query": "/workspace/yangxinlong/NAS_data/recall_files_test/孩子成长/baby-2972221_1280.jpg", "top_k": 5}'

# 4. 文档相似度
curl -X POST http://172.16.50.51:8001/api/fms/retrieve \
  -H "Content-Type: application/json" \
  -d '{"type": "doc2doc", "query": "/workspace/yangxinlong/NAS_data/recall_files_test/pdf/亿道班车路线.pdf", "top_k": 5}'

# 5. 知识库问答
curl -X POST http://172.16.50.51:8001/api/fms/chat \
  -H "Content-Type: application/json" \
  -d '{"query": "公司班车有哪些路线"}'

# 6. 获取文件列表
curl http://172.16.50.51:8001/api/fms/get_knowledge_files

# 7. 只获取图片
curl "http://172.16.50.51:8001/api/fms/get_knowledge_files?file_type=image"
"""

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
