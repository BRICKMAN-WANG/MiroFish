"""Tests for Zep-related data classes (to_dict / to_text serialisation)."""

import pytest

from app.services.zep_entity_reader import EntityNode, FilteredEntities
from app.services.zep_tools import (
    SearchResult,
    NodeInfo,
    EdgeInfo,
    InsightForgeResult,
    PanoramaResult,
    AgentInterview,
    InterviewResult,
)


# --------------- EntityNode ---------------

class TestEntityNode:
    @pytest.fixture
    def entity(self):
        return EntityNode(
            uuid="abc-123",
            name="测试实体",
            labels=["Entity", "Person", "Student"],
            summary="一个学生",
            attributes={"age": 20},
            related_edges=[{"direction": "outgoing", "edge_name": "studies_at", "target_node_uuid": "node-b"}],
            related_nodes=[{"uuid": "node-b", "name": "学校", "labels": ["Entity", "School"], "summary": ""}],
        )

    def test_to_dict(self, entity):
        d = entity.to_dict()
        assert d["uuid"] == "abc-123"
        assert d["name"] == "测试实体"
        assert d["labels"] == ["Entity", "Person", "Student"]
        assert d["summary"] == "一个学生"
        assert d["attributes"] == {"age": 20}
        assert len(d["related_edges"]) == 1
        assert len(d["related_nodes"]) == 1

    def test_get_entity_type(self, entity):
        assert entity.get_entity_type() == "Person"

    def test_get_entity_type_default_labels(self):
        entity = EntityNode(uuid="x", name="x", labels=["Entity"], summary="", attributes={})
        assert entity.get_entity_type() is None

    def test_get_entity_type_only_node(self):
        entity = EntityNode(uuid="x", name="x", labels=["Node"], summary="", attributes={})
        assert entity.get_entity_type() is None


# --------------- FilteredEntities ---------------

class TestFilteredEntities:
    def test_to_dict(self):
        entities = [
            EntityNode(uuid="1", name="A", labels=["Person"], summary="", attributes={}),
            EntityNode(uuid="2", name="B", labels=["Org"], summary="", attributes={}),
        ]
        fe = FilteredEntities(
            entities=entities,
            entity_types={"Person", "Org"},
            total_count=10,
            filtered_count=2,
        )
        d = fe.to_dict()
        assert d["total_count"] == 10
        assert d["filtered_count"] == 2
        assert len(d["entities"]) == 2
        assert set(d["entity_types"]) == {"Person", "Org"}


# --------------- SearchResult ---------------

class TestSearchResult:
    def test_to_dict(self):
        sr = SearchResult(
            facts=["fact1", "fact2"],
            edges=[{"name": "edge1"}],
            nodes=[{"name": "node1"}],
            query="test query",
            total_count=2,
        )
        d = sr.to_dict()
        assert d["facts"] == ["fact1", "fact2"]
        assert d["total_count"] == 2
        assert d["query"] == "test query"

    def test_to_text(self):
        sr = SearchResult(
            facts=["事实1", "事实2"],
            edges=[],
            nodes=[],
            query="查询",
            total_count=2,
        )
        text = sr.to_text()
        assert "查询" in text
        assert "事实1" in text
        assert "事实2" in text
        assert "2" in text

    def test_to_text_no_facts(self):
        sr = SearchResult(facts=[], edges=[], nodes=[], query="q", total_count=0)
        text = sr.to_text()
        assert "0" in text


# --------------- NodeInfo ---------------

class TestNodeInfo:
    def test_to_dict(self):
        ni = NodeInfo(
            uuid="n1", name="Node1", labels=["Entity", "Person"],
            summary="A person", attributes={"age": 30},
        )
        d = ni.to_dict()
        assert d["name"] == "Node1"
        assert d["attributes"] == {"age": 30}

    def test_to_text(self):
        ni = NodeInfo(uuid="n1", name="张三", labels=["Entity", "Person"], summary="医生", attributes={})
        text = ni.to_text()
        assert "张三" in text
        assert "医生" in text
        assert "Person" in text


# --------------- EdgeInfo ---------------

class TestEdgeInfo:
    @pytest.fixture
    def edge(self):
        return EdgeInfo(
            uuid="e1",
            name="works_at",
            fact="张三在某医院工作",
            source_node_uuid="n1",
            target_node_uuid="n2",
            source_node_name="张三",
            target_node_name="某医院",
            created_at="2025-01-01",
            valid_at="2025-01-01",
            invalid_at=None,
            expired_at=None,
        )

    def test_to_dict(self, edge):
        d = edge.to_dict()
        assert d["name"] == "works_at"
        assert d["fact"] == "张三在某医院工作"
        assert d["source_node_name"] == "张三"

    def test_to_text_default(self, edge):
        text = edge.to_text()
        assert "张三" in text
        assert "某医院" in text
        assert "works_at" in text

    def test_to_text_with_temporal(self, edge):
        text = edge.to_text(include_temporal=True)
        assert "2025-01-01" in text

    def test_is_expired(self, edge):
        assert edge.is_expired is False
        edge.expired_at = "2025-06-01"
        assert edge.is_expired is True

    def test_is_invalid(self, edge):
        assert edge.is_invalid is False
        edge.invalid_at = "2025-06-01"
        assert edge.is_invalid is True

    def test_to_text_no_names_falls_back_to_uuid(self):
        edge = EdgeInfo(
            uuid="e1", name="rel", fact="fact",
            source_node_uuid="src-uuid-long", target_node_uuid="tgt-uuid-long",
        )
        text = edge.to_text()
        # Should use truncated UUIDs
        assert "src-uuid" in text


# --------------- InsightForgeResult ---------------

class TestInsightForgeResult:
    @pytest.fixture
    def result(self):
        return InsightForgeResult(
            query="未来教育趋势",
            simulation_requirement="模拟教育发展",
            sub_queries=["子问题1", "子问题2"],
            semantic_facts=["事实1", "事实2"],
            entity_insights=[{"name": "学校A", "type": "School", "summary": "重点学校"}],
            relationship_chains=["学校A -->[合作]--> 公司B"],
            total_facts=2,
            total_entities=1,
            total_relationships=1,
        )

    def test_to_dict(self, result):
        d = result.to_dict()
        assert d["query"] == "未来教育趋势"
        assert d["total_facts"] == 2

    def test_to_text(self, result):
        text = result.to_text()
        assert "未来教育趋势" in text
        assert "子问题1" in text
        assert "事实1" in text
        assert "学校A" in text
        assert "合作" in text


# --------------- PanoramaResult ---------------

class TestPanoramaResult:
    @pytest.fixture
    def result(self):
        nodes = [NodeInfo(uuid="n1", name="实体A", labels=["Entity", "Person"], summary="", attributes={})]
        edges = [
            EdgeInfo(
                uuid="e1", name="related", fact="事实1",
                source_node_uuid="n1", target_node_uuid="n2",
                source_node_name="实体A", target_node_name="实体B",
            )
        ]
        return PanoramaResult(
            query="全景搜索",
            all_nodes=nodes,
            all_edges=edges,
            active_facts=["当前事实"],
            historical_facts=["历史事实"],
            total_nodes=1,
            total_edges=1,
            active_count=1,
            historical_count=1,
        )

    def test_to_dict(self, result):
        d = result.to_dict()
        assert d["query"] == "全景搜索"
        assert d["active_count"] == 1
        assert len(d["all_nodes"]) == 1

    def test_to_text(self, result):
        text = result.to_text()
        assert "全景搜索" in text
        assert "当前事实" in text
        assert "历史事实" in text
        assert "实体A" in text


# --------------- AgentInterview & InterviewResult ---------------

class TestAgentInterview:
    @pytest.fixture
    def interview(self):
        return AgentInterview(
            agent_name="张三",
            agent_role="学生",
            agent_bio="一名大学生",
            question="你对未来的看法？",
            response="我认为教育会越来越个性化",
            key_quotes=["教育将更加个性化", "技术进步推动教育变革"],
        )

    def test_to_dict(self, interview):
        d = interview.to_dict()
        assert d["agent_name"] == "张三"
        assert d["agent_role"] == "学生"

    def test_to_text(self, interview):
        text = interview.to_text()
        assert "张三" in text
        assert "你对未来的看法？" in text
        assert "我认为教育会越来越个性化" in text
        # "教育将更加个性化" is 8 chars, filtered by len>=10 check;
        # "技术进步推动教育变革" is 10 chars, so it should appear
        assert "技术进步推动教育变革" in text

    def test_key_quote_skip_too_short(self):
        interview = AgentInterview(
            agent_name="A", agent_role="R", agent_bio="B",
            question="Q", response="R",
            key_quotes=["短", "足够长的有意义的引言内容"],
        )
        text = interview.to_text()
        # "短" should be filtered out (len < 10)
        assert "短" not in text
        assert "足够长的有意义的引言内容" in text

    def test_key_quote_truncate_long(self):
        long_quote = "A" * 200
        interview = AgentInterview(
            agent_name="A", agent_role="R", agent_bio="B",
            question="Q", response="R",
            key_quotes=[long_quote],
        )
        text = interview.to_text()
        assert len(text) < 500  # Should be truncated


class TestInterviewResult:
    def test_to_dict(self):
        interview = AgentInterview(
            agent_name="李四", agent_role="教师", agent_bio="B",
            question="Q", response="R",
        )
        ir = InterviewResult(
            interview_topic="教育话题",
            interview_questions=["Q1", "Q2"],
            selected_agents=[{"name": "李四", "profession": "教师"}],
            interviews=[interview],
            selection_reasoning="相关度高",
            summary="采访摘要内容",
            total_agents=3,
            interviewed_count=1,
        )
        d = ir.to_dict()
        assert d["interview_topic"] == "教育话题"
        assert d["interviewed_count"] == 1
        assert len(d["interviews"]) == 1

    def test_to_text(self):
        interview = AgentInterview(
            agent_name="王五", agent_role="工程师", agent_bio="B",
            question="Q", response="A",
        )
        ir = InterviewResult(
            interview_topic="科技发展",
            interview_questions=["Q1"],
            selected_agents=[],
            interviews=[interview],
            selection_reasoning="理由",
            summary="摘要",
            total_agents=1,
            interviewed_count=1,
        )
        text = ir.to_text()
        assert "科技发展" in text
        assert "王五" in text
        assert "摘要" in text

    def test_to_text_no_interviews(self):
        ir = InterviewResult(
            interview_topic="空采访",
            interview_questions=[],
            selected_agents=[],
            interviews=[],
            total_agents=0,
            interviewed_count=0,
        )
        text = ir.to_text()
        assert "无采访记录" in text
