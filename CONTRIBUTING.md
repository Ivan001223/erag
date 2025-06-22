# 贡献指南

欢迎为智能知识库系统贡献代码！本文档将指导您如何参与项目开发。

## 开始之前

### 环境准备
- Python 3.11+
- Node.js 18+
- Docker 20.10+
- Git 2.30+

### 开发工具
- IDE: VS Code / PyCharm
- 代码格式化: Black, isort
- 类型检查: mypy
- 测试框架: pytest
- 前端工具: Vue 3, TypeScript, Vite

## 开发流程

### 1. Fork 和 Clone
```bash
# Fork 项目到您的GitHub账户
# 然后克隆到本地
git clone https://github.com/your-username/knowledge-system.git
cd knowledge-system

# 添加上游仓库
git remote add upstream https://github.com/original-org/knowledge-system.git
```

### 2. 创建开发分支
```bash
# 从main分支创建功能分支
git checkout -b feature/your-feature-name

# 或者修复分支
git checkout -b fix/issue-number
```

### 3. 设置开发环境
```bash
# 后端环境
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
pip install -r requirements-test.txt

# 前端环境
cd frontend
npm install

# 启动开发服务
docker-compose up -d postgres neo4j redis minio
uvicorn backend.main:app --reload
npm run dev
```

## 代码规范

### Python代码规范

#### 格式化工具
```bash
# 代码格式化
black backend/
isort backend/

# 代码检查
flake8 backend/
mypy backend/

# 安全检查
bandit -r backend/
```

#### 代码风格
```python
# 好的示例
class EntityService:
    """实体服务类，处理实体相关业务逻辑"""
    
    def __init__(self, repository: EntityRepository):
        self.repository = repository
    
    async def create_entity(
        self, 
        entity_data: EntityCreate
    ) -> Entity:
        """创建新实体
        
        Args:
            entity_data: 实体创建数据
            
        Returns:
            创建的实体对象
            
        Raises:
            ValidationError: 数据验证失败
            DuplicateError: 实体已存在
        """
        # 验证数据
        if await self.repository.exists_by_name(entity_data.name):
            raise DuplicateError(f"实体 {entity_data.name} 已存在")
        
        # 创建实体
        entity = Entity(**entity_data.dict())
        return await self.repository.create(entity)
```

#### 类型注解
```python
from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel

# 函数类型注解
async def search_entities(
    query: str,
    entity_type: Optional[str] = None,
    limit: int = 20,
    offset: int = 0
) -> List[Entity]:
    pass

# 类型别名
EntityID = str
EntityDict = Dict[str, Any]
SearchResult = List[Entity]
```

### TypeScript代码规范

#### ESLint配置
```json
{
  "extends": [
    "@vue/typescript/recommended",
    "@vue/prettier",
    "@vue/prettier/@typescript-eslint"
  ],
  "rules": {
    "@typescript-eslint/no-unused-vars": "error",
    "@typescript-eslint/explicit-function-return-type": "warn",
    "vue/component-name-in-template-casing": ["error", "PascalCase"]
  }
}
```

#### 代码风格
```typescript
// 接口定义
interface Entity {
  id: string;
  name: string;
  entityType: EntityType;
  description?: string;
  properties: Record<string, any>;
  createdAt: Date;
  updatedAt: Date;
}

// 组件定义
export default defineComponent({
  name: 'EntityList',
  props: {
    entities: {
      type: Array as PropType<Entity[]>,
      required: true
    },
    loading: {
      type: Boolean,
      default: false
    }
  },
  emits: ['select', 'delete'],
  setup(props, { emit }) {
    const handleSelect = (entity: Entity): void => {
      emit('select', entity);
    };
    
    return {
      handleSelect
    };
  }
});
```

## 测试要求

### 后端测试

#### 单元测试
```python
# tests/unit/test_entity_service.py
import pytest
from unittest.mock import AsyncMock

from backend.services.entity_service import EntityService
from backend.models.entity import Entity
from backend.schemas.entity import EntityCreate

class TestEntityService:
    @pytest.fixture
    def mock_repository(self):
        return AsyncMock()
    
    @pytest.fixture
    def entity_service(self, mock_repository):
        return EntityService(mock_repository)
    
    async def test_create_entity_success(self, entity_service, mock_repository):
        # Arrange
        entity_data = EntityCreate(
            name="测试实体",
            entity_type="CONCEPT"
        )
        mock_repository.exists_by_name.return_value = False
        mock_repository.create.return_value = Entity(id="123", **entity_data.dict())
        
        # Act
        result = await entity_service.create_entity(entity_data)
        
        # Assert
        assert result.name == "测试实体"
        mock_repository.create.assert_called_once()
```

#### 集成测试
```python
# tests/integration/test_api_integration.py
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_create_entity_api(client: AsyncClient, auth_headers):
    # 创建实体
    response = await client.post(
        "/api/v1/entities",
        headers=auth_headers,
        json={
            "name": "集成测试实体",
            "entity_type": "CONCEPT"
        }
    )
    
    assert response.status_code == 201
    data = response.json()
    assert data["success"] is True
    assert data["data"]["name"] == "集成测试实体"
```

### 前端测试

#### 组件测试
```typescript
// tests/components/EntityList.spec.ts
import { mount } from '@vue/test-utils';
import EntityList from '@/components/EntityList.vue';

describe('EntityList', () => {
  const mockEntities = [
    {
      id: '1',
      name: '测试实体1',
      entityType: 'PERSON',
      description: '测试描述',
      properties: {},
      createdAt: new Date(),
      updatedAt: new Date()
    }
  ];

  it('renders entity list correctly', () => {
    const wrapper = mount(EntityList, {
      props: {
        entities: mockEntities
      }
    });

    expect(wrapper.find('.entity-item').exists()).toBe(true);
    expect(wrapper.text()).toContain('测试实体1');
  });

  it('emits select event when entity is clicked', async () => {
    const wrapper = mount(EntityList, {
      props: {
        entities: mockEntities
      }
    });

    await wrapper.find('.entity-item').trigger('click');
    expect(wrapper.emitted('select')).toBeTruthy();
  });
});
```

### 测试覆盖率
```bash
# 后端测试覆盖率
pytest --cov=backend --cov-report=html --cov-report=term

# 前端测试覆盖率
npm run test:coverage
```

## 提交规范

### Commit Message格式
```
type(scope): description

[optional body]

[optional footer]
```

### 类型说明
- `feat`: 新功能
- `fix`: 修复bug
- `docs`: 文档更新
- `style`: 代码格式调整
- `refactor`: 代码重构
- `test`: 测试相关
- `chore`: 构建或工具相关

### 示例
```bash
feat(api): 添加实体搜索接口

实现基于名称和类型的实体搜索功能，支持分页和排序。

- 添加搜索API端点
- 实现搜索逻辑
- 添加单元测试
- 更新API文档

Closes #123
```

## Pull Request流程

### 1. 创建PR前检查
```bash
# 运行所有测试
make test

# 代码质量检查
make lint

# 类型检查
make type-check

# 安全检查
make security-check
```

### 2. PR模板
```markdown
## 变更描述
简要描述本次变更的内容和目的。

## 变更类型
- [ ] 新功能
- [ ] Bug修复
- [ ] 文档更新
- [ ] 代码重构
- [ ] 性能优化
- [ ] 其他

## 测试
- [ ] 添加了新的测试
- [ ] 所有测试通过
- [ ] 手动测试完成

## 检查清单
- [ ] 代码遵循项目规范
- [ ] 添加了必要的文档
- [ ] 更新了CHANGELOG
- [ ] 考虑了向后兼容性

## 相关Issue
Closes #issue_number

## 截图（如适用）
```

### 3. 代码审查

#### 审查要点
- **功能正确性**: 代码是否实现了预期功能
- **代码质量**: 是否遵循最佳实践
- **性能影响**: 是否有性能问题
- **安全性**: 是否存在安全风险
- **测试覆盖**: 是否有足够的测试
- **文档完整**: 是否有必要的文档

#### 审查流程
1. 自动化检查通过
2. 至少2名维护者审查
3. 所有反馈得到解决
4. 合并到主分支

## 发布流程

### 版本号规范
遵循[语义版本控制](https://semver.org/lang/zh-CN/)：
- `MAJOR.MINOR.PATCH`
- 主版本号：不兼容的API修改
- 次版本号：向下兼容的功能性新增
- 修订号：向下兼容的问题修正

### 发布检查清单
- [ ] 所有测试通过
- [ ] 文档已更新
- [ ] CHANGELOG已更新
- [ ] 版本号已更新
- [ ] 安全扫描通过
- [ ] 性能测试通过

## 社区参与

### 报告问题
使用[Issue模板](https://github.com/org/repo/issues/new/choose)报告：
- Bug报告
- 功能请求
- 文档改进
- 性能问题

### 讨论交流
- [GitHub Discussions](https://github.com/org/repo/discussions)
- [Slack频道](https://slack.workspace.com)
- [邮件列表](mailto:dev@project.com)

### 贡献类型
- 代码贡献
- 文档改进
- 测试用例
- Bug报告
- 功能建议
- 设计反馈

## 开发工具配置

### VS Code配置
```json
{
  "python.defaultInterpreterPath": "./backend/venv/bin/python",
  "python.formatting.provider": "black",
  "python.linting.enabled": true,
  "python.linting.flake8Enabled": true,
  "python.linting.mypyEnabled": true,
  "editor.formatOnSave": true,
  "editor.codeActionsOnSave": {
    "source.organizeImports": true
  }
}
```

### Git Hooks
```bash
# 安装pre-commit
pip install pre-commit
pre-commit install

# .pre-commit-config.yaml
repos:
  - repo: https://github.com/psf/black
    rev: 22.3.0
    hooks:
      - id: black
  - repo: https://github.com/pycqa/isort
    rev: 5.10.1
    hooks:
      - id: isort
  - repo: https://github.com/pycqa/flake8
    rev: 4.0.1
    hooks:
      - id: flake8
```

## 常见问题

### Q: 如何运行特定的测试？
```bash
# 运行特定测试文件
pytest tests/unit/test_entity_service.py

# 运行特定测试函数
pytest tests/unit/test_entity_service.py::test_create_entity

# 运行特定标记的测试
pytest -m "not slow"
```

### Q: 如何调试应用？
```bash
# 启动调试模式
uvicorn backend.main:app --reload --log-level debug

# 使用调试器
import pdb; pdb.set_trace()
```

### Q: 如何更新依赖？
```bash
# 更新Python依赖
pip-compile requirements.in
pip-compile requirements-test.in

# 更新Node.js依赖
npm update
```