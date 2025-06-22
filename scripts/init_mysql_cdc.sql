-- MySQL CDC 初始化脚本
-- 创建支持CDC的数据库结构和配置

-- 创建数据库
CREATE DATABASE IF NOT EXISTS erag CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE erag;

-- 创建CDC用户并授权
CREATE USER IF NOT EXISTS 'cdc_user'@'%' IDENTIFIED BY 'cdc_password123';
GRANT SELECT, RELOAD, SHOW DATABASES, REPLICATION SLAVE, REPLICATION CLIENT ON *.* TO 'cdc_user'@'%';
GRANT ALL PRIVILEGES ON erag.* TO 'cdc_user'@'%';
FLUSH PRIVILEGES;

-- =============================================
-- 业务数据表（CDC源表）
-- =============================================

-- 创建文档表（主要的CDC源表）
CREATE TABLE IF NOT EXISTS documents (
    id VARCHAR(36) PRIMARY KEY DEFAULT (UUID()),
    title VARCHAR(500) NOT NULL COMMENT '文档标题',
    content LONGTEXT COMMENT '文档内容',
    doc_type VARCHAR(50) DEFAULT 'text' COMMENT '文档类型：text, pdf, word, excel, ppt等',
    source_path VARCHAR(1000) COMMENT '源文件路径',
    file_size BIGINT DEFAULT 0 COMMENT '文件大小（字节）',
    page_count INT DEFAULT 0 COMMENT '页数',
    language VARCHAR(10) DEFAULT 'zh' COMMENT '语言',
    metadata JSON COMMENT '元数据',
    vector_status VARCHAR(20) DEFAULT 'pending' COMMENT '向量化状态',
    kg_status VARCHAR(20) DEFAULT 'pending' COMMENT '知识图谱状态',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    is_deleted BOOLEAN DEFAULT FALSE COMMENT '是否删除',
    INDEX idx_doc_type (doc_type),
    INDEX idx_vector_status (vector_status),
    INDEX idx_kg_status (kg_status),
    INDEX idx_created_at (created_at),
    INDEX idx_updated_at (updated_at)
) ENGINE=InnoDB COMMENT='文档表';

-- 创建文档块表
CREATE TABLE IF NOT EXISTS document_chunks (
    id VARCHAR(36) PRIMARY KEY DEFAULT (UUID()),
    document_id VARCHAR(36) NOT NULL COMMENT '文档ID',
    chunk_index INT NOT NULL COMMENT '块索引',
    content TEXT NOT NULL COMMENT '块内容',
    chunk_size INT NOT NULL COMMENT '块大小',
    overlap_size INT DEFAULT 0 COMMENT '重叠大小',
    metadata JSON COMMENT '元数据',
    embedding_vector JSON COMMENT '嵌入向量',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    is_deleted BOOLEAN DEFAULT FALSE,
    INDEX idx_document_id (document_id),
    INDEX idx_chunk_index (chunk_index),
    INDEX idx_created_at (created_at),
    FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
) ENGINE=InnoDB COMMENT='文档块表';

-- 创建实体表
CREATE TABLE IF NOT EXISTS entities (
    id VARCHAR(36) PRIMARY KEY DEFAULT (UUID()),
    name VARCHAR(255) NOT NULL COMMENT '实体名称',
    entity_type VARCHAR(100) NOT NULL COMMENT '实体类型',
    description TEXT COMMENT '实体描述',
    properties JSON COMMENT '实体属性（JSON格式）',
    confidence DECIMAL(3,2) DEFAULT 0.00 COMMENT '置信度（0-1）',
    source_documents JSON COMMENT '来源文档',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    is_deleted BOOLEAN DEFAULT FALSE,
    INDEX idx_name (name),
    INDEX idx_entity_type (entity_type),
    INDEX idx_confidence (confidence),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB COMMENT='实体表';

-- 创建关系表
CREATE TABLE IF NOT EXISTS relations (
    id VARCHAR(36) PRIMARY KEY DEFAULT (UUID()),
    source_id VARCHAR(36) NOT NULL COMMENT '源实体ID',
    target_id VARCHAR(36) NOT NULL COMMENT '目标实体ID',
    relation_type VARCHAR(100) NOT NULL COMMENT '关系类型',
    properties JSON COMMENT '关系属性（JSON格式）',
    confidence DECIMAL(3,2) DEFAULT 0.00 COMMENT '置信度（0-1）',
    source_documents JSON COMMENT '来源文档',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    is_deleted BOOLEAN DEFAULT FALSE,
    INDEX idx_source_id (source_id),
    INDEX idx_target_id (target_id),
    INDEX idx_relation_type (relation_type),
    INDEX idx_confidence (confidence),
    INDEX idx_created_at (created_at),
    FOREIGN KEY (source_id) REFERENCES entities(id) ON DELETE CASCADE,
    FOREIGN KEY (target_id) REFERENCES entities(id) ON DELETE CASCADE
) ENGINE=InnoDB COMMENT='关系表';

-- 创建向量表
CREATE TABLE IF NOT EXISTS vectors (
    id VARCHAR(36) PRIMARY KEY DEFAULT (UUID()),
    text TEXT COMMENT '文本内容',
    vector JSON COMMENT '向量数据',
    model VARCHAR(100) COMMENT '模型名称',
    vector_type VARCHAR(50) COMMENT '向量类型',
    dimension INT COMMENT '向量维度',
    source_id VARCHAR(255) COMMENT '来源ID',
    source_type VARCHAR(100) COMMENT '来源类型',
    chunk_index INT COMMENT '块索引',
    page_number INT COMMENT '页码',
    language VARCHAR(10) COMMENT '语言',
    metadata JSON COMMENT '元数据',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    is_deleted BOOLEAN DEFAULT FALSE,
    INDEX idx_source_id (source_id),
    INDEX idx_source_type (source_type),
    INDEX idx_model (model),
    INDEX idx_vector_type (vector_type),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB COMMENT='向量表';

-- =============================================
-- 系统元数据表
-- =============================================

-- 创建任务表
CREATE TABLE IF NOT EXISTS tasks (
    id VARCHAR(36) PRIMARY KEY DEFAULT (UUID()),
    task_type VARCHAR(50) NOT NULL COMMENT '任务类型',
    status VARCHAR(50) NOT NULL COMMENT '任务状态',
    input_data JSON COMMENT '输入数据',
    output_data JSON COMMENT '输出数据',
    error_message TEXT COMMENT '错误信息',
    progress DECIMAL(5,2) DEFAULT 0.00 COMMENT '进度',
    priority INT DEFAULT 0 COMMENT '优先级',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    is_deleted BOOLEAN DEFAULT FALSE,
    INDEX idx_task_type (task_type),
    INDEX idx_status (status),
    INDEX idx_priority (priority),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB COMMENT='任务表';

-- 创建查询日志表
CREATE TABLE IF NOT EXISTS query_logs (
    id VARCHAR(36) PRIMARY KEY DEFAULT (UUID()),
    user_id VARCHAR(64) COMMENT '用户ID',
    query TEXT NOT NULL COMMENT '查询内容',
    search_type VARCHAR(50) COMMENT '搜索类型',
    result_count INT DEFAULT 0 COMMENT '结果数量',
    response_time DECIMAL(10,3) COMMENT '响应时间',
    metadata JSON COMMENT '元数据',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    is_deleted BOOLEAN DEFAULT FALSE,
    INDEX idx_user_id (user_id),
    INDEX idx_search_type (search_type),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB COMMENT='查询日志表';

-- 创建指标表
CREATE TABLE IF NOT EXISTS metrics (
    id VARCHAR(36) PRIMARY KEY DEFAULT (UUID()),
    metric_name VARCHAR(100) NOT NULL COMMENT '指标名称',
    metric_value DECIMAL(15,4) NOT NULL COMMENT '指标值',
    metric_type VARCHAR(50) COMMENT '指标类型',
    tags JSON COMMENT '标签',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    is_deleted BOOLEAN DEFAULT FALSE,
    INDEX idx_metric_name (metric_name),
    INDEX idx_metric_type (metric_type),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB COMMENT='指标表';

-- 创建配置表
CREATE TABLE IF NOT EXISTS configs (
    id VARCHAR(36) PRIMARY KEY DEFAULT (UUID()),
    config_key VARCHAR(255) NOT NULL COMMENT '配置键',
    value TEXT COMMENT '配置值',
    data_type VARCHAR(50) COMMENT '数据类型',
    config_type VARCHAR(50) COMMENT '配置类型',
    scope VARCHAR(50) COMMENT '作用域',
    scope_id VARCHAR(255) COMMENT '作用域ID',
    description TEXT COMMENT '描述',
    default_value TEXT COMMENT '默认值',
    validation_rules JSON COMMENT '验证规则',
    is_sensitive BOOLEAN DEFAULT FALSE COMMENT '是否敏感',
    is_readonly BOOLEAN DEFAULT FALSE COMMENT '是否只读',
    status VARCHAR(50) DEFAULT 'active' COMMENT '状态',
    version INT DEFAULT 1 COMMENT '版本',
    created_by VARCHAR(255) COMMENT '创建者',
    updated_by VARCHAR(255) COMMENT '更新者',
    tags JSON COMMENT '标签',
    metadata JSON COMMENT '元数据',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    is_deleted BOOLEAN DEFAULT FALSE,
    UNIQUE KEY uk_config (config_key, scope, scope_id),
    INDEX idx_config_type (config_type),
    INDEX idx_scope (scope),
    INDEX idx_status (status)
) ENGINE=InnoDB COMMENT='配置表';

-- 创建配置历史表
CREATE TABLE IF NOT EXISTS config_history (
    id VARCHAR(36) PRIMARY KEY DEFAULT (UUID()),
    config_key VARCHAR(255) NOT NULL COMMENT '配置键',
    old_value TEXT COMMENT '旧值',
    new_value TEXT COMMENT '新值',
    scope VARCHAR(50) COMMENT '作用域',
    scope_id VARCHAR(255) COMMENT '作用域ID',
    change_type VARCHAR(50) COMMENT '变更类型',
    changed_by VARCHAR(255) COMMENT '变更者',
    change_reason TEXT COMMENT '变更原因',
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '时间戳',
    metadata JSON COMMENT '元数据',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    is_deleted BOOLEAN DEFAULT FALSE,
    INDEX idx_config_key (config_key),
    INDEX idx_timestamp (timestamp),
    INDEX idx_changed_by (changed_by)
) ENGINE=InnoDB COMMENT='配置历史表';

-- 创建配置模板表
CREATE TABLE IF NOT EXISTS config_templates (
    id VARCHAR(36) PRIMARY KEY DEFAULT (UUID()),
    name VARCHAR(255) NOT NULL COMMENT '模板名称',
    description TEXT COMMENT '模板描述',
    template_data JSON COMMENT '模板数据',
    category VARCHAR(100) COMMENT '分类',
    version VARCHAR(50) COMMENT '版本',
    is_default BOOLEAN DEFAULT FALSE COMMENT '是否默认',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    is_deleted BOOLEAN DEFAULT FALSE,
    INDEX idx_name (name),
    INDEX idx_category (category),
    INDEX idx_version (version)
) ENGINE=InnoDB COMMENT='配置模板表';

-- 创建ETL作业表
CREATE TABLE IF NOT EXISTS etl_jobs (
    id VARCHAR(36) PRIMARY KEY DEFAULT (UUID()),
    name VARCHAR(255) NOT NULL COMMENT '作业名称',
    description TEXT COMMENT '作业描述',
    job_type VARCHAR(50) COMMENT '作业类型',
    source_config JSON COMMENT '源配置',
    target_config JSON COMMENT '目标配置',
    steps_config JSON COMMENT '步骤配置',
    schedule_config VARCHAR(255) COMMENT '调度配置',
    config JSON COMMENT '配置',
    status VARCHAR(50) COMMENT '状态',
    priority INT COMMENT '优先级',
    created_by VARCHAR(255) COMMENT '创建者',
    start_time TIMESTAMP NULL COMMENT '开始时间',
    end_time TIMESTAMP NULL COMMENT '结束时间',
    last_run_time TIMESTAMP NULL COMMENT '最后运行时间',
    next_run_time TIMESTAMP NULL COMMENT '下次运行时间',
    run_count INT DEFAULT 0 COMMENT '运行次数',
    success_count INT DEFAULT 0 COMMENT '成功次数',
    failure_count INT DEFAULT 0 COMMENT '失败次数',
    error_message TEXT COMMENT '错误信息',
    metrics JSON COMMENT '指标',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    is_deleted BOOLEAN DEFAULT FALSE,
    INDEX idx_name (name),
    INDEX idx_job_type (job_type),
    INDEX idx_status (status),
    INDEX idx_created_by (created_by)
) ENGINE=InnoDB COMMENT='ETL作业表';

-- 创建ETL作业运行记录表
CREATE TABLE IF NOT EXISTS etl_job_runs (
    id VARCHAR(36) PRIMARY KEY DEFAULT (UUID()),
    job_id VARCHAR(36) NOT NULL COMMENT '作业ID',
    run_number INT COMMENT '运行编号',
    status VARCHAR(50) COMMENT '状态',
    start_time TIMESTAMP NULL COMMENT '开始时间',
    end_time TIMESTAMP NULL COMMENT '结束时间',
    duration_seconds INT COMMENT '持续时间(秒)',
    records_processed INT DEFAULT 0 COMMENT '处理记录数',
    records_success INT DEFAULT 0 COMMENT '成功记录数',
    records_failed INT DEFAULT 0 COMMENT '失败记录数',
    error_message TEXT COMMENT '错误信息',
    step_results JSON COMMENT '步骤结果',
    metrics JSON COMMENT '指标',
    logs JSON COMMENT '日志',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    is_deleted BOOLEAN DEFAULT FALSE,
    INDEX idx_job_id (job_id),
    INDEX idx_status (status),
    INDEX idx_start_time (start_time),
    FOREIGN KEY (job_id) REFERENCES etl_jobs(id) ON DELETE CASCADE
) ENGINE=InnoDB COMMENT='ETL作业运行记录表';

-- 创建ETL指标表
CREATE TABLE IF NOT EXISTS etl_metrics (
    id VARCHAR(36) PRIMARY KEY DEFAULT (UUID()),
    job_id VARCHAR(36) COMMENT '作业ID',
    run_id VARCHAR(36) COMMENT '运行ID',
    metric_name VARCHAR(100) COMMENT '指标名称',
    metric_value DECIMAL(15,4) COMMENT '指标值',
    metric_type VARCHAR(50) COMMENT '指标类型',
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '时间戳',
    tags JSON COMMENT '标签',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    is_deleted BOOLEAN DEFAULT FALSE,
    INDEX idx_job_id (job_id),
    INDEX idx_run_id (run_id),
    INDEX idx_metric_name (metric_name),
    INDEX idx_timestamp (timestamp)
) ENGINE=InnoDB COMMENT='ETL指标表';

-- =============================================
-- 知识图谱元数据表
-- =============================================

-- 创建知识图谱表
CREATE TABLE IF NOT EXISTS graphs (
    id VARCHAR(36) PRIMARY KEY DEFAULT (UUID()),
    name VARCHAR(255) NOT NULL COMMENT '图名称',
    description TEXT COMMENT '图描述',
    metadata JSON COMMENT '元数据JSON',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    is_deleted BOOLEAN DEFAULT FALSE,
    INDEX idx_name (name),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB COMMENT='知识图谱表';

-- 创建知识图谱实体表
CREATE TABLE IF NOT EXISTS graph_entities (
    id VARCHAR(36) PRIMARY KEY DEFAULT (UUID()),
    name VARCHAR(255) NOT NULL COMMENT '实体名称',
    entity_type VARCHAR(100) NOT NULL COMMENT '实体类型',
    properties TEXT COMMENT '属性JSON',
    metadata TEXT COMMENT '元数据JSON',
    graph_id VARCHAR(36) NOT NULL COMMENT '图ID',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    is_deleted BOOLEAN DEFAULT FALSE,
    INDEX idx_graph_id (graph_id),
    INDEX idx_name (name),
    INDEX idx_entity_type (entity_type),
    INDEX idx_created_at (created_at),
    FOREIGN KEY (graph_id) REFERENCES graphs(id) ON DELETE CASCADE
) ENGINE=InnoDB COMMENT='知识图谱实体表';

-- 创建知识图谱关系表
CREATE TABLE IF NOT EXISTS graph_relations (
    id VARCHAR(36) PRIMARY KEY DEFAULT (UUID()),
    source_id VARCHAR(36) NOT NULL COMMENT '源实体ID',
    target_id VARCHAR(36) NOT NULL COMMENT '目标实体ID',
    relation_type VARCHAR(100) NOT NULL COMMENT '关系类型',
    properties TEXT COMMENT '属性JSON',
    metadata TEXT COMMENT '元数据JSON',
    confidence DECIMAL(3,2) DEFAULT 1.0 COMMENT '置信度',
    graph_id VARCHAR(36) NOT NULL COMMENT '图ID',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    is_deleted BOOLEAN DEFAULT FALSE,
    INDEX idx_graph_id (graph_id),
    INDEX idx_source_id (source_id),
    INDEX idx_target_id (target_id),
    INDEX idx_relation_type (relation_type),
    INDEX idx_confidence (confidence),
    INDEX idx_created_at (created_at),
    FOREIGN KEY (graph_id) REFERENCES graphs(id) ON DELETE CASCADE,
    FOREIGN KEY (source_id) REFERENCES graph_entities(id) ON DELETE CASCADE,
    FOREIGN KEY (target_id) REFERENCES graph_entities(id) ON DELETE CASCADE
) ENGINE=InnoDB COMMENT='知识图谱关系表';

-- 创建知识图谱统计表
CREATE TABLE IF NOT EXISTS graph_statistics (
    id VARCHAR(36) PRIMARY KEY DEFAULT (UUID()),
    graph_id VARCHAR(36) NOT NULL COMMENT '图ID',
    entity_count INT DEFAULT 0 COMMENT '实体数量',
    relation_count INT DEFAULT 0 COMMENT '关系数量',
    node_degree_avg DECIMAL(10,2) DEFAULT 0.00 COMMENT '平均节点度',
    clustering_coefficient DECIMAL(5,4) DEFAULT 0.0000 COMMENT '聚类系数',
    diameter INT DEFAULT 0 COMMENT '图直径',
    density DECIMAL(10,8) DEFAULT 0.00000000 COMMENT '图密度',
    computed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '计算时间',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    is_deleted BOOLEAN DEFAULT FALSE,
    INDEX idx_graph_id (graph_id),
    INDEX idx_computed_at (computed_at),
    FOREIGN KEY (graph_id) REFERENCES graphs(id) ON DELETE CASCADE
) ENGINE=InnoDB COMMENT='知识图谱统计表';

-- =============================================
-- 用户和权限相关表
-- =============================================

-- 创建用户表
CREATE TABLE IF NOT EXISTS users (
    id VARCHAR(36) PRIMARY KEY DEFAULT (UUID()),
    username VARCHAR(50) UNIQUE NOT NULL COMMENT '用户名',
    email VARCHAR(100) UNIQUE NOT NULL COMMENT '邮箱',
    password_hash VARCHAR(255) NOT NULL COMMENT '密码哈希',
    full_name VARCHAR(100) COMMENT '全名',
    is_active BOOLEAN DEFAULT TRUE COMMENT '是否激活',
    is_superuser BOOLEAN DEFAULT FALSE COMMENT '是否超级用户',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    is_deleted BOOLEAN DEFAULT FALSE,
    INDEX idx_username (username),
    INDEX idx_email (email),
    INDEX idx_is_active (is_active)
) ENGINE=InnoDB COMMENT='用户表';

-- 创建知识库表
CREATE TABLE IF NOT EXISTS knowledge_bases (
    id VARCHAR(36) PRIMARY KEY DEFAULT (UUID()),
    name VARCHAR(200) NOT NULL COMMENT '知识库名称',
    description TEXT COMMENT '知识库描述',
    owner_id VARCHAR(36) NOT NULL COMMENT '所有者ID',
    is_public BOOLEAN DEFAULT FALSE COMMENT '是否公开',
    settings LONGTEXT COMMENT '知识库设置(JSON)',
    metadata LONGTEXT COMMENT '元数据(JSON)',
    document_count INT DEFAULT 0 COMMENT '文档数量',
    chunk_count INT DEFAULT 0 COMMENT '文档块数量',
    total_size BIGINT DEFAULT 0 COMMENT '总大小(字节)',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    is_deleted BOOLEAN DEFAULT FALSE,
    INDEX idx_owner_id (owner_id),
    INDEX idx_is_public (is_public),
    INDEX idx_name (name),
    FOREIGN KEY (owner_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB COMMENT='知识库表';

-- 创建通知表
CREATE TABLE IF NOT EXISTS notifications (
    id VARCHAR(36) PRIMARY KEY DEFAULT (UUID()),
    user_id VARCHAR(36) NOT NULL COMMENT '用户ID',
    title VARCHAR(200) NOT NULL COMMENT '通知标题',
    content TEXT NOT NULL COMMENT '通知内容',
    notification_type VARCHAR(50) DEFAULT 'info' COMMENT '通知类型',
    priority INT DEFAULT 1 COMMENT '优先级',
    metadata TEXT COMMENT '元数据JSON',
    is_read BOOLEAN DEFAULT FALSE COMMENT '是否已读',
    expires_at TIMESTAMP NULL COMMENT '过期时间',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    is_deleted BOOLEAN DEFAULT FALSE,
    INDEX idx_user_id (user_id),
    INDEX idx_is_read (is_read),
    INDEX idx_notification_type (notification_type),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB COMMENT='通知表';

-- =============================================
-- CDC监控相关表
-- =============================================

-- 创建CDC监控表
CREATE TABLE IF NOT EXISTS cdc_monitoring (
    id VARCHAR(36) PRIMARY KEY DEFAULT (UUID()),
    job_id VARCHAR(255) NOT NULL COMMENT 'Flink作业ID',
    job_name VARCHAR(255) NOT NULL COMMENT '作业名称',
    source_table VARCHAR(255) NOT NULL COMMENT '源表名',
    target_table VARCHAR(255) NOT NULL COMMENT '目标表名',
    lag_ms BIGINT DEFAULT 0 COMMENT '延迟毫秒数',
    records_processed BIGINT DEFAULT 0 COMMENT '已处理记录数',
    last_checkpoint_time TIMESTAMP NULL COMMENT '最后检查点时间',
    status ENUM('running', 'stopped', 'failed', 'paused') DEFAULT 'running',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    is_deleted BOOLEAN DEFAULT FALSE,
    INDEX idx_job_id (job_id),
    INDEX idx_status (status),
    INDEX idx_lag_ms (lag_ms)
) ENGINE=InnoDB COMMENT='CDC监控表';

-- 插入示例数据
INSERT INTO documents (title, content, doc_type, source_path, file_size) VALUES
('人工智能技术概览', '人工智能（AI）是计算机科学的一个分支，致力于创建能够执行通常需要人类智能的任务的系统。', 'text', '/docs/ai_overview.txt', 1024),
('机器学习基础', '机器学习是人工智能的一个子集，它使计算机能够在没有明确编程的情况下学习和改进。', 'text', '/docs/ml_basics.txt', 2048),
('深度学习原理', '深度学习是机器学习的一个子集，使用多层神经网络来模拟人脑的工作方式。', 'text', '/docs/dl_principles.txt', 3072);

INSERT INTO entities (name, entity_type, description, source_documents, confidence) VALUES
('人工智能', 'CONCEPT', '计算机科学分支，模拟人类智能', '[1]', 0.95),
('机器学习', 'CONCEPT', '人工智能子集，自动学习算法', '[2]', 0.90),
('深度学习', 'CONCEPT', '机器学习子集，多层神经网络', '[3]', 0.88),
('神经网络', 'TECHNOLOGY', '模拟人脑神经元的计算模型', '[3]', 0.85);

INSERT INTO relations (source_id, target_id, relation_type, source_documents, confidence) VALUES
('2', '1', 'IS_SUBSET_OF', '["2"]', 0.90),
('3', '2', 'IS_SUBSET_OF', '["3"]', 0.88),
('4', '3', 'USED_IN', '["3"]', 0.85);

-- 创建CDC配置验证视图
CREATE VIEW cdc_config_check AS
SELECT 
    'log_bin' as config_name,
    @@log_bin as config_value,
    CASE WHEN @@log_bin = 1 THEN 'OK' ELSE 'ERROR' END as status
UNION ALL
SELECT 
    'binlog_format' as config_name,
    @@binlog_format as config_value,
    CASE WHEN @@binlog_format = 'ROW' THEN 'OK' ELSE 'WARNING' END as status
UNION ALL
SELECT 
    'binlog_row_image' as config_name,
    @@binlog_row_image as config_value,
    CASE WHEN @@binlog_row_image = 'FULL' THEN 'OK' ELSE 'WARNING' END as status
UNION ALL
SELECT 
    'server_id' as config_name,
    CAST(@@server_id AS CHAR) as config_value,
    CASE WHEN @@server_id > 0 THEN 'OK' ELSE 'ERROR' END as status
UNION ALL
SELECT 
    'gtid_mode' as config_name,
    @@gtid_mode as config_value,
    CASE WHEN @@gtid_mode = 'ON' THEN 'OK' ELSE 'WARNING' END as status;

-- 创建存储过程：检查CDC配置
DELIMITER //
CREATE PROCEDURE CheckCDCConfig()
BEGIN
    DECLARE done INT DEFAULT FALSE;
    DECLARE config_name VARCHAR(50);
    DECLARE config_value VARCHAR(100);
    DECLARE config_status VARCHAR(20);
    DECLARE error_count INT DEFAULT 0;
    DECLARE warning_count INT DEFAULT 0;
    
    DECLARE cur CURSOR FOR SELECT config_name, config_value, status FROM cdc_config_check;
    DECLARE CONTINUE HANDLER FOR NOT FOUND SET done = TRUE;
    
    -- 创建临时表存储结果
    DROP TEMPORARY TABLE IF EXISTS cdc_check_result;
    CREATE TEMPORARY TABLE cdc_check_result (
        config_name VARCHAR(50),
        config_value VARCHAR(100),
        status VARCHAR(20)
    );
    
    OPEN cur;
    read_loop: LOOP
        FETCH cur INTO config_name, config_value, config_status;
        IF done THEN
            LEAVE read_loop;
        END IF;
        
        INSERT INTO cdc_check_result VALUES (config_name, config_value, config_status);
        
        IF config_status = 'ERROR' THEN
            SET error_count = error_count + 1;
        ELSEIF config_status = 'WARNING' THEN
            SET warning_count = warning_count + 1;
        END IF;
    END LOOP;
    CLOSE cur;
    
    -- 显示检查结果
    SELECT * FROM cdc_check_result;
    
    -- 显示总结
    SELECT 
        error_count as errors,
        warning_count as warnings,
        CASE 
            WHEN error_count = 0 AND warning_count = 0 THEN 'CDC配置完全正确'
            WHEN error_count = 0 THEN 'CDC配置基本正确，有警告'
            ELSE 'CDC配置有错误，需要修复'
        END as overall_status;
        
    DROP TEMPORARY TABLE cdc_check_result;
END //
DELIMITER ;

-- 创建函数：获取当前binlog位置
DELIMITER //
CREATE FUNCTION GetBinlogPosition() RETURNS JSON
READS SQL DATA
DETERMINISTIC
BEGIN
    DECLARE binlog_file VARCHAR(255);
    DECLARE binlog_position BIGINT;
    DECLARE result JSON;
    
    SELECT File, Position INTO binlog_file, binlog_position 
    FROM (SHOW MASTER STATUS) as master_status LIMIT 1;
    
    SET result = JSON_OBJECT(
        'file', IFNULL(binlog_file, ''),
        'position', IFNULL(binlog_position, 0),
        'timestamp', NOW()
    );
    
    RETURN result;
END //
DELIMITER ;

-- 验证CDC配置
CALL CheckCDCConfig();

-- 显示初始化完成信息
SELECT 
    'MySQL CDC 初始化完成' as message,
    DATABASE() as current_database,
    USER() as current_user,
    NOW() as timestamp;

-- 显示当前binlog状态
SHOW MASTER STATUS; 