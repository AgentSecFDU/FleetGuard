import React, { useState, useEffect, useCallback } from 'react';
import {
  Table, Card, Tag, Button, Space, Typography, Drawer, Modal, Input,
  Descriptions, Popconfirm, message, Empty,
} from 'antd';
import {
  PlusOutlined, EyeOutlined, EditOutlined, SendOutlined,
  HistoryOutlined, ReloadOutlined,
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import { policiesApi } from '../api/endpoints';
import type { Policy, PolicyVersion, PaginatedResponse } from '../types';

const { Title, Paragraph } = Typography;
const { TextArea } = Input;

const STATUS_COLORS: Record<string, string> = {
  draft: 'orange',
  published: 'green',
  archived: 'gray',
};

// ── Basic YAML syntax highlighter ──────────────────────────────────
function highlightYaml(yaml: string): React.ReactNode {
  if (!yaml) return null;
  const lines = yaml.split('\n');
  return (
    <pre style={{
      background: '#1e1e2e',
      color: '#cdd6f4',
      padding: 16,
      borderRadius: 6,
      overflow: 'auto',
      maxHeight: 500,
      fontSize: 13,
      lineHeight: 1.7,
      fontFamily: 'ui-monospace, SFMono-Regular, Consolas, "Liberation Mono", Menlo, monospace',
      margin: 0,
      whiteSpace: 'pre-wrap',
      wordBreak: 'break-word',
    }}>
      {lines.map((line, i) => (
        <div key={i} style={{ minHeight: '1.7em' }}>
          <span style={{ color: '#585b70', marginRight: 12, userSelect: 'none', display: 'inline-block', width: 28, textAlign: 'right' }}>
            {i + 1}
          </span>
          <span>{highlightLine(line)}</span>
        </div>
      ))}
    </pre>
  );
}

function highlightLine(line: string): React.ReactNode {
  // Comment
  if (/^\s*#/.test(line)) {
    return <span style={{ color: '#6c7086' }}>{line}</span>;
  }
  // Key-value pair
  const kvMatch = line.match(/^(\s*)([\w.-]+)(\s*:\s*)(.*)$/);
  if (kvMatch) {
    const [, indent, key, colon, value] = kvMatch;
    const trimmedVal = value.trim();
    let valueNode: React.ReactNode = value;
    if (trimmedVal === 'true' || trimmedVal === 'false') {
      valueNode = <span style={{ color: '#fab387' }}>{value}</span>;
    } else if (/^-?\d+(\.\d+)?$/.test(trimmedVal)) {
      valueNode = <span style={{ color: '#fab387' }}>{value}</span>;
    } else if (/^".*"$/.test(trimmedVal) || /^'.*'$/.test(trimmedVal)) {
      valueNode = <span style={{ color: '#a6e3a1' }}>{value}</span>;
    } else if (trimmedVal === 'null' || trimmedVal === '~') {
      valueNode = <span style={{ color: '#f38ba8' }}>{value}</span>;
    } else if (value !== '') {
      valueNode = <span style={{ color: '#a6e3a1' }}>{value}</span>;
    }
    return (
      <>
        {indent}
        <span style={{ color: '#89b4fa' }}>{key}</span>
        <span style={{ color: '#cdd6f4' }}>{colon}</span>
        {valueNode}
      </>
    );
  }
  // List item
  if (/^\s*-\s/.test(line)) {
    const indent = line.match(/^(\s*)/)?.[0] ?? '';
    const dashIndex = line.indexOf('-');
    const rest = line.slice(dashIndex + 1);
    return (
      <>
        {indent}
        <span style={{ color: '#f9e2af' }}>-</span>
        <span style={{ color: '#a6e3a1' }}>{rest}</span>
      </>
    );
  }
  return <>{line}</>;
}

// ── Components ─────────────────────────────────────────────────────

export default function PoliciesPage() {
  const [policies, setPolicies] = useState<Policy[]>([]);
  const [loading, setLoading] = useState(false);

  // Create / Edit modal state
  const [createModalOpen, setCreateModalOpen] = useState(false);
  const [createLoading, setCreateLoading] = useState(false);
  const [newPolicyId, setNewPolicyId] = useState('');
  const [newPolicyName, setNewPolicyName] = useState('');
  const [newYamlContent, setNewYamlContent] = useState('');

  // Edit modal state
  const [editModalOpen, setEditModalOpen] = useState(false);
  const [editLoading, setEditLoading] = useState(false);
  const [editingPolicy, setEditingPolicy] = useState<Policy | null>(null);
  const [editYamlContent, setEditYamlContent] = useState('');

  // View drawer state
  const [viewDrawerOpen, setViewDrawerOpen] = useState(false);
  const [viewingPolicy, setViewingPolicy] = useState<Policy | null>(null);

  // History drawer state
  const [historyDrawerOpen, setHistoryDrawerOpen] = useState(false);
  const [historyVersions, setHistoryVersions] = useState<PolicyVersion[]>([]);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [historyPolicyId, setHistoryPolicyId] = useState('');

  // ── Fetch policies ─────────────────────────────────────────────────
  const fetchPolicies = useCallback(async () => {
    setLoading(true);
    try {
      const resp = await policiesApi.list();
      const body = resp.data as PaginatedResponse<Policy>;
      setPolicies(body.data ?? []);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to load policies';
      message.error(msg);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchPolicies();
  }, [fetchPolicies]);

  // ── Create ─────────────────────────────────────────────────────────
  const handleCreateOpen = () => {
    setNewPolicyId('');
    setNewPolicyName('');
    setNewYamlContent('');
    setCreateModalOpen(true);
  };

  const handleCreate = async () => {
    // Basic required field validation
    if (!newPolicyId.trim() || !newPolicyName.trim()) {
      message.warning('Policy ID and Name are required.');
      return;
    }

    setCreateLoading(true);
    try {
      // Validate YAML first
      await policiesApi.validate({
        policy_id: newPolicyId.trim(),
        name: newPolicyName.trim(),
        yaml_content: newYamlContent,
      });
    } catch (err: unknown) {
      let errMsg = 'YAML validation failed';
      if (err && typeof err === 'object' && 'response' in err) {
        const axiosErr = err as { response?: { data?: { detail?: unknown } } };
        const detail = axiosErr.response?.data?.detail;
        if (detail) {
          if (Array.isArray(detail)) {
            errMsg = detail.map((d: { msg?: string; loc?: string[] }) =>
              `${d.loc?.join('.') ?? 'root'}: ${d.msg ?? 'invalid'}`
            ).join('; ');
          } else if (typeof detail === 'string') {
            errMsg = detail;
          } else {
            errMsg = JSON.stringify(detail);
          }
        }
      }
      message.error(errMsg);
      setCreateLoading(false);
      return;
    }

    try {
      await policiesApi.create({
        policy_id: newPolicyId.trim(),
        name: newPolicyName.trim(),
        yaml_content: newYamlContent,
      });
      message.success(`Policy "${newPolicyId}" created successfully.`);
      setCreateModalOpen(false);
      fetchPolicies();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to create policy';
      message.error(msg);
    } finally {
      setCreateLoading(false);
    }
  };

  // ── Edit ───────────────────────────────────────────────────────────
  const handleEditOpen = (policy: Policy) => {
    setEditingPolicy(policy);
    setEditYamlContent(policy.yaml_content);
    setEditModalOpen(true);
  };

  const handleEditSave = async () => {
    if (!editingPolicy) return;
    setEditLoading(true);
    try {
      // Validate YAML first
      await policiesApi.validate({
        policy_id: editingPolicy.policy_id,
        name: editingPolicy.name,
        yaml_content: editYamlContent,
      });
    } catch (err: unknown) {
      let errMsg = 'YAML validation failed';
      if (err && typeof err === 'object' && 'response' in err) {
        const axiosErr = err as { response?: { data?: { detail?: unknown } } };
        const detail = axiosErr.response?.data?.detail;
        if (detail) {
          if (Array.isArray(detail)) {
            errMsg = detail.map((d: { msg?: string; loc?: string[] }) =>
              `${d.loc?.join('.') ?? 'root'}: ${d.msg ?? 'invalid'}`
            ).join('; ');
          } else if (typeof detail === 'string') {
            errMsg = detail;
          } else {
            errMsg = JSON.stringify(detail);
          }
        }
      }
      message.error(errMsg);
      setEditLoading(false);
      return;
    }

    try {
      await policiesApi.update(editingPolicy.policy_id, editYamlContent);
      message.success(`Policy "${editingPolicy.policy_id}" updated.`);
      setEditModalOpen(false);
      setEditingPolicy(null);
      fetchPolicies();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to update policy';
      message.error(msg);
    } finally {
      setEditLoading(false);
    }
  };

  // ── View ───────────────────────────────────────────────────────────
  const handleViewOpen = (policy: Policy) => {
    setViewingPolicy(policy);
    setViewDrawerOpen(true);
  };

  // ── Publish ────────────────────────────────────────────────────────
  const handlePublish = async (policyId: string) => {
    try {
      await policiesApi.publish(policyId);
      message.success(`Policy "${policyId}" published.`);
      fetchPolicies();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to publish policy';
      message.error(msg);
    }
  };

  // ── History ────────────────────────────────────────────────────────
  const handleHistoryOpen = async (policyId: string) => {
    setHistoryPolicyId(policyId);
    setHistoryDrawerOpen(true);
    setHistoryLoading(true);
    try {
      const resp = await policiesApi.getVersions(policyId);
      const body = resp.data;
      // The API might return an array directly or wrapped
      const versions: PolicyVersion[] = Array.isArray(body) ? body : (body as { versions?: PolicyVersion[] }).versions ?? [];
      setHistoryVersions(versions);
    } catch (err: unknown) {
      message.error('Failed to load version history');
      setHistoryVersions([]);
    } finally {
      setHistoryLoading(false);
    }
  };

  // ── Table columns ──────────────────────────────────────────────────
  const columns: ColumnsType<Policy> = [
    {
      title: 'Policy ID',
      dataIndex: 'policy_id',
      key: 'policy_id',
      width: 200,
      ellipsis: true,
    },
    {
      title: 'Name',
      dataIndex: 'name',
      key: 'name',
      width: 200,
      ellipsis: true,
    },
    {
      title: 'Version',
      dataIndex: 'version',
      key: 'version',
      width: 80,
      align: 'center',
      render: (v: number) => <span style={{ fontWeight: 600 }}>v{v}</span>,
    },
    {
      title: 'Status',
      dataIndex: 'status',
      key: 'status',
      width: 110,
      align: 'center',
      render: (s: string) => (
        <Tag color={STATUS_COLORS[s] ?? 'default'}>
          {s.toUpperCase()}
        </Tag>
      ),
    },
    {
      title: 'Created By',
      dataIndex: 'created_by',
      key: 'created_by',
      width: 140,
      ellipsis: true,
      render: (v: string | null) => v ?? '-',
    },
    {
      title: 'Published At',
      dataIndex: 'published_at',
      key: 'published_at',
      width: 180,
      render: (v: string | null) => v ? new Date(v).toLocaleString() : '-',
    },
    {
      title: 'Actions',
      key: 'actions',
      width: 300,
      render: (_, record: Policy) => (
        <Space size="small" wrap>
          <Button
            type="link"
            size="small"
            icon={<EyeOutlined />}
            onClick={(e) => { e.stopPropagation(); handleViewOpen(record); }}
          >
            View
          </Button>
          <Button
            type="link"
            size="small"
            icon={<EditOutlined />}
            onClick={(e) => { e.stopPropagation(); handleEditOpen(record); }}
          >
            Edit
          </Button>
          {record.status !== 'published' && (
            <Popconfirm
              title={`Publish policy "${record.policy_id}"?`}
              description="Once published, devices will begin pulling this policy version."
              onConfirm={(e) => { e?.stopPropagation(); handlePublish(record.policy_id); }}
              onCancel={(e) => e?.stopPropagation()}
              okText="Publish"
              cancelText="Cancel"
            >
              <Button
                type="link"
                size="small"
                icon={<SendOutlined />}
                style={{ color: '#52c41a' }}
                onClick={(e) => e.stopPropagation()}
              >
                Publish
              </Button>
            </Popconfirm>
          )}
          <Button
            type="link"
            size="small"
            icon={<HistoryOutlined />}
            onClick={(e) => { e.stopPropagation(); handleHistoryOpen(record.policy_id); }}
          >
            History
          </Button>
        </Space>
      ),
    },
  ];

  // ── Render ─────────────────────────────────────────────────────────
  return (
    <div>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <Title level={2} style={{ margin: 0 }}>Policies</Title>
        <Space>
          <Button icon={<ReloadOutlined />} onClick={fetchPolicies}>Refresh</Button>
          <Button type="primary" icon={<PlusOutlined />} onClick={handleCreateOpen}>
            New Policy
          </Button>
        </Space>
      </div>

      {/* Table */}
      <Card size="small">
        <Table<Policy>
          columns={columns}
          dataSource={policies}
          rowKey="policy_id"
          loading={loading}
          pagination={policies.length > 10 ? { pageSize: 10, showSizeChanger: true } : false}
          size="small"
          scroll={{ x: 1000 }}
        />
      </Card>

      {/* ── Create Policy Modal ───────────────────────────────────── */}
      <Modal
        title="New Policy"
        open={createModalOpen}
        onCancel={() => setCreateModalOpen(false)}
        onOk={handleCreate}
        confirmLoading={createLoading}
        okText="Create"
        width={640}
        destroyOnClose
      >
        <div style={{ marginBottom: 16 }}>
          <label style={{ display: 'block', marginBottom: 4, fontWeight: 500 }}>Policy ID</label>
          <Input
            placeholder="e.g., default-agent-policy"
            value={newPolicyId}
            onChange={e => setNewPolicyId(e.target.value)}
          />
        </div>
        <div style={{ marginBottom: 16 }}>
          <label style={{ display: 'block', marginBottom: 4, fontWeight: 500 }}>Name</label>
          <Input
            placeholder="e.g., Default Agent Policy"
            value={newPolicyName}
            onChange={e => setNewPolicyName(e.target.value)}
          />
        </div>
        <div>
          <label style={{ display: 'block', marginBottom: 4, fontWeight: 500 }}>YAML Content</label>
          <TextArea
            rows={16}
            placeholder={`# Example policy YAML
rules:
  - name: block-sensitive-files
    tool_categories: [file]
    action: deny
    conditions:
      path_pattern: "/etc/**"
  - name: allow-readonly
    tool_categories: [shell]
    action: allow
    risk_threshold: medium`}
            value={newYamlContent}
            onChange={e => setNewYamlContent(e.target.value)}
            style={{ fontFamily: 'ui-monospace, SFMono-Regular, Consolas, monospace', fontSize: 13 }}
          />
        </div>
      </Modal>

      {/* ── Edit Policy Modal ─────────────────────────────────────── */}
      <Modal
        title={editingPolicy ? `Edit: ${editingPolicy.policy_id}` : 'Edit Policy'}
        open={editModalOpen}
        onCancel={() => { setEditModalOpen(false); setEditingPolicy(null); }}
        onOk={handleEditSave}
        confirmLoading={editLoading}
        okText="Update"
        width={720}
        destroyOnClose
      >
        {editingPolicy && (
          <>
            <Descriptions size="small" column={2} style={{ marginBottom: 16 }}>
              <Descriptions.Item label="Policy ID">{editingPolicy.policy_id}</Descriptions.Item>
              <Descriptions.Item label="Name">{editingPolicy.name}</Descriptions.Item>
              <Descriptions.Item label="Version">v{editingPolicy.version}</Descriptions.Item>
              <Descriptions.Item label="Status">
                <Tag color={STATUS_COLORS[editingPolicy.status]}>{editingPolicy.status.toUpperCase()}</Tag>
              </Descriptions.Item>
            </Descriptions>
            <label style={{ display: 'block', marginBottom: 4, fontWeight: 500 }}>YAML Content</label>
            <TextArea
              rows={20}
              value={editYamlContent}
              onChange={e => setEditYamlContent(e.target.value)}
              style={{ fontFamily: 'ui-monospace, SFMono-Regular, Consolas, monospace', fontSize: 13 }}
            />
          </>
        )}
      </Modal>

      {/* ── View Policy Drawer ────────────────────────────────────── */}
      <Drawer
        title={viewingPolicy ? `Policy: ${viewingPolicy.policy_id}` : 'Policy View'}
        open={viewDrawerOpen}
        onClose={() => { setViewDrawerOpen(false); setViewingPolicy(null); }}
        width={700}
      >
        {viewingPolicy && (
          <>
            <Descriptions size="small" column={2} bordered style={{ marginBottom: 20 }}>
              <Descriptions.Item label="Policy ID">{viewingPolicy.policy_id}</Descriptions.Item>
              <Descriptions.Item label="Name">{viewingPolicy.name}</Descriptions.Item>
              <Descriptions.Item label="Version">v{viewingPolicy.version}</Descriptions.Item>
              <Descriptions.Item label="Status">
                <Tag color={STATUS_COLORS[viewingPolicy.status]}>{viewingPolicy.status.toUpperCase()}</Tag>
              </Descriptions.Item>
              <Descriptions.Item label="Created By">{viewingPolicy.created_by ?? '-'}</Descriptions.Item>
              <Descriptions.Item label="Published At">
                {viewingPolicy.published_at ? new Date(viewingPolicy.published_at).toLocaleString() : '-'}
              </Descriptions.Item>
              <Descriptions.Item label="Created At" span={2}>
                {new Date(viewingPolicy.created_at).toLocaleString()}
              </Descriptions.Item>
              <Descriptions.Item label="Updated At" span={2}>
                {new Date(viewingPolicy.updated_at).toLocaleString()}
              </Descriptions.Item>
            </Descriptions>
            <Paragraph strong style={{ marginBottom: 8 }}>YAML Content</Paragraph>
            {highlightYaml(viewingPolicy.yaml_content)}
          </>
        )}
      </Drawer>

      {/* ── History Drawer ────────────────────────────────────────── */}
      <Drawer
        title={`Version History: ${historyPolicyId}`}
        open={historyDrawerOpen}
        onClose={() => { setHistoryDrawerOpen(false); setHistoryVersions([]); }}
        width={500}
      >
        {historyLoading ? (
          <div style={{ textAlign: 'center', padding: 40 }}>Loading...</div>
        ) : historyVersions.length === 0 ? (
          <Empty description="No version history found" />
        ) : (
          <Table<PolicyVersion>
            dataSource={historyVersions}
            rowKey="version"
            pagination={false}
            size="small"
            columns={[
              {
                title: 'Version',
                dataIndex: 'version',
                key: 'version',
                width: 80,
                render: (v: number) => <strong>v{v}</strong>,
              },
              {
                title: 'Status',
                dataIndex: 'status',
                key: 'status',
                width: 110,
                render: (s: string) => (
                  <Tag color={STATUS_COLORS[s] ?? 'default'}>{s.toUpperCase()}</Tag>
                ),
              },
              {
                title: 'Published At',
                dataIndex: 'published_at',
                key: 'published_at',
                width: 180,
                render: (v: string | null) => v ? new Date(v).toLocaleString() : '-',
              },
              {
                title: 'Created At',
                dataIndex: 'created_at',
                key: 'created_at',
                width: 180,
                render: (v: string) => new Date(v).toLocaleString(),
              },
            ]}
          />
        )}
      </Drawer>
    </div>
  );
}
