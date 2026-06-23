import React, { useState, useEffect, useCallback, useRef } from 'react';
import {
  Table, Card, Tag, Select, Input, DatePicker, Modal, Button, Space,
  Typography, Tooltip, Descriptions, Row, Col,
} from 'antd';
import {
  SearchOutlined, ReloadOutlined, ExportOutlined,
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import { eventsApi } from '../api/endpoints';
import { WS_URL } from '../utils/config';
import type { Event, PaginatedResponse } from '../types';

const { Title } = Typography;
const { RangePicker } = DatePicker;

const SEVERITY_COLORS: Record<string, string> = {
  low: 'green',
  medium: 'orange',
  high: 'red',
  critical: 'magenta',
};

const DECISION_COLORS: Record<string, string> = {
  allow: 'green',
  deny: 'red',
  warn: 'orange',
  audit: 'blue',
};

function formatTimestamp(ts: string): string {
  if (!ts) return '-';
  try {
    return new Date(ts).toLocaleString();
  } catch {
    return ts;
  }
}

export default function EventsPage() {
  const [events, setEvents] = useState<Event[]>([]);
  const [loading, setLoading] = useState(false);
  const [nextCursor, setNextCursor] = useState<string | null>(null);
  const [hasMore, setHasMore] = useState(true);
  const [selectedEvent, setSelectedEvent] = useState<Event | null>(null);
  const [detailOpen, setDetailOpen] = useState(false);
  const [highlightedIds, setHighlightedIds] = useState<Set<string>>(new Set());

  // Filters
  const [filterDeviceId, setFilterDeviceId] = useState('');
  const [filterSeverity, setFilterSeverity] = useState<string | undefined>(undefined);
  const [filterEventType, setFilterEventType] = useState<string | undefined>(undefined);
  const [filterToolCategory, setFilterToolCategory] = useState<string | undefined>(undefined);
  const [filterPolicyDecision, setFilterPolicyDecision] = useState<string | undefined>(undefined);
  const [filterDateFrom, setFilterDateFrom] = useState<string | undefined>(undefined);
  const [filterDateTo, setFilterDateTo] = useState<string | undefined>(undefined);

  // Ref for highlight timeouts so we can clean them up
  const highlightTimers = useRef<ReturnType<typeof setTimeout>[]>([]);

  // ── Fetch events ──────────────────────────────────────────────────
  const fetchEvents = useCallback(async (cursor?: string | null, reset = false) => {
    setLoading(true);
    try {
      const params: Record<string, unknown> = {};
      if (cursor) params.cursor = cursor;
      if (filterDeviceId) params.device_id = filterDeviceId;
      if (filterSeverity) params.severity = filterSeverity;
      if (filterEventType) params.event_type = filterEventType;
      if (filterToolCategory) params.tool_category = filterToolCategory;
      if (filterPolicyDecision) params.policy_decision = filterPolicyDecision;
      if (filterDateFrom) params.timestamp_from = filterDateFrom;
      if (filterDateTo) params.timestamp_to = filterDateTo;
      params.limit = 50;

      const resp = await eventsApi.list(params);
      const body = resp.data as PaginatedResponse<Event>;
      const newEvents = body.data ?? [];

      if (reset) {
        setEvents(newEvents);
      } else {
        setEvents(prev => [...prev, ...newEvents]);
      }

      const next = body.pagination.cursor ?? null;
      setNextCursor(next);
      setHasMore(!!next);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to load events';
      console.error(msg);
    } finally {
      setLoading(false);
    }
  }, [filterDeviceId, filterSeverity, filterEventType, filterToolCategory, filterPolicyDecision, filterDateFrom, filterDateTo]);

  // Initial load + reload on filter change
  useEffect(() => {
    fetchEvents(null, true);
  }, [fetchEvents]);

  // ── WebSocket for real-time events ────────────────────────────────
  useEffect(() => {
    const token = localStorage.getItem('access_token');
    if (!token) return;

    const ws = new WebSocket(`${WS_URL}?token=${encodeURIComponent(token)}`);

    ws.onopen = () => {
      console.log('[Events] WebSocket connected');
    };

    ws.onmessage = (e) => {
      try {
        const msg = JSON.parse(e.data);
        if (msg.type === 'event' && msg.data) {
          const newEvent = msg.data as Event;
          // Only prepend high/critical events with highlight animation
          if (newEvent.severity === 'high' || newEvent.severity === 'critical') {
            setEvents(prev => [newEvent, ...prev]);
            // Highlight the new row briefly
            setHighlightedIds(prev => {
              const next = new Set(prev);
              next.add(newEvent.event_id);
              return next;
            });
            const timer = setTimeout(() => {
              setHighlightedIds(prev => {
                const next = new Set(prev);
                next.delete(newEvent.event_id);
                return next;
              });
            }, 3000);
            highlightTimers.current.push(timer);
          }
        }
      } catch {
        // ignore malformed messages
      }
    };

    ws.onerror = (err) => {
      console.error('[Events] WebSocket error', err);
    };

    ws.onclose = () => {
      console.log('[Events] WebSocket disconnected');
    };

    return () => {
      ws.close();
      // Clear all pending highlight timers
      highlightTimers.current.forEach(clearTimeout);
      highlightTimers.current = [];
    };
  }, []);

  // ── Handlers ─────────────────────────────────────────────────────
  const handleSearch = () => {
    fetchEvents(null, true);
  };

  const handleLoadMore = () => {
    if (nextCursor && !loading) {
      fetchEvents(nextCursor);
    }
  };

  const handleRowClick = useCallback(async (record: Event) => {
    try {
      // Fetch full event detail
      const resp = await eventsApi.get(record.event_id);
      setSelectedEvent(resp.data as Event);
    } catch {
      // fallback to the row data
      setSelectedEvent(record);
    }
    setDetailOpen(true);
  }, []);

  const handleCloseDetail = () => {
    setDetailOpen(false);
    setSelectedEvent(null);
  };

  const handleClearFilters = () => {
    setFilterDeviceId('');
    setFilterSeverity(undefined);
    setFilterEventType(undefined);
    setFilterToolCategory(undefined);
    setFilterPolicyDecision(undefined);
    setFilterDateFrom(undefined);
    setFilterDateTo(undefined);
  };

  // ── Table columns ────────────────────────────────────────────────
  const columns: ColumnsType<Event> = [
    {
      title: 'Severity',
      dataIndex: 'severity',
      key: 'severity',
      width: 90,
      render: (s: string | null) => {
        if (!s) return <Tag>-</Tag>;
        return <Tag color={SEVERITY_COLORS[s] ?? 'default'}>{s.toUpperCase()}</Tag>;
      },
    },
    {
      title: 'Event Type',
      dataIndex: 'event_type',
      key: 'event_type',
      width: 130,
      ellipsis: true,
    },
    {
      title: 'Device ID',
      dataIndex: 'device_id',
      key: 'device_id',
      width: 160,
      ellipsis: true,
    },
    {
      title: 'Hostname',
      dataIndex: 'hostname',
      key: 'hostname',
      width: 120,
      ellipsis: true,
      render: (v: string | null) => v ?? '-',
    },
    {
      title: 'Tool',
      dataIndex: 'tool_name',
      key: 'tool_name',
      width: 120,
      ellipsis: true,
      render: (v: string | null) => v ?? '-',
    },
    {
      title: 'Category',
      dataIndex: 'tool_category',
      key: 'tool_category',
      width: 100,
      ellipsis: true,
      render: (v: string | null) => v ?? '-',
    },
    {
      title: 'Params',
      dataIndex: 'params_summary',
      key: 'params_summary',
      width: 180,
      ellipsis: true,
      render: (v: string | null) => {
        if (!v) return '-';
        const truncated = v.length > 80 ? v.slice(0, 80) + '…' : v;
        return (
          <Tooltip title={v} placement="topLeft" overlayStyle={{ maxWidth: 500 }}>
            <span style={{ cursor: 'pointer', fontSize: 13 }}>{truncated}</span>
          </Tooltip>
        );
      },
    },
    {
      title: 'Risk',
      dataIndex: 'risk_score',
      key: 'risk_score',
      width: 70,
      sorter: (a, b) => a.risk_score - b.risk_score,
      render: (v: number) => {
        const color = v >= 80 ? 'red' : v >= 50 ? 'orange' : 'green';
        return <span style={{ fontWeight: 600, color }}>{v}</span>;
      },
    },
    {
      title: 'Decision',
      dataIndex: 'policy_decision',
      key: 'policy_decision',
      width: 100,
      render: (d: string | null) => {
        if (!d) return <Tag>-</Tag>;
        return <Tag color={DECISION_COLORS[d] ?? 'default'}>{d.toUpperCase()}</Tag>;
      },
    },
    {
      title: 'Timestamp',
      dataIndex: 'timestamp',
      key: 'timestamp',
      width: 180,
      render: (v: string) => formatTimestamp(v),
    },
  ];

  // ── Render ───────────────────────────────────────────────────────
  return (
    <div>
      <Title level={2} style={{ marginTop: 0 }}>Events</Title>

      {/* Filter bar */}
      <Card size="small" style={{ marginBottom: 16 }}>
        <Row gutter={[12, 12]} align="middle">
          <Col>
            <Input
              placeholder="Device ID"
              value={filterDeviceId}
              onChange={e => setFilterDeviceId(e.target.value)}
              style={{ width: 180 }}
              prefix={<SearchOutlined />}
              allowClear
            />
          </Col>
          <Col>
            <Select
              placeholder="Severity"
              value={filterSeverity}
              onChange={setFilterSeverity}
              allowClear
              style={{ width: 130 }}
              options={[
                { value: 'low', label: 'Low' },
                { value: 'medium', label: 'Medium' },
                { value: 'high', label: 'High' },
                { value: 'critical', label: 'Critical' },
              ]}
            />
          </Col>
          <Col>
            <Select
              placeholder="Event Type"
              value={filterEventType}
              onChange={setFilterEventType}
              allowClear
              style={{ width: 160 }}
              options={[
                { value: 'tool_call', label: 'Tool Call' },
                { value: 'session_start', label: 'Session Start' },
                { value: 'session_end', label: 'Session End' },
                { value: 'file_access', label: 'File Access' },
                { value: 'network_access', label: 'Network Access' },
                { value: 'command_exec', label: 'Command Exec' },
                { value: 'auth_event', label: 'Auth Event' },
              ]}
            />
          </Col>
          <Col>
            <Select
              placeholder="Tool Category"
              value={filterToolCategory}
              onChange={setFilterToolCategory}
              allowClear
              style={{ width: 160 }}
              options={[
                { value: 'file', label: 'File' },
                { value: 'network', label: 'Network' },
                { value: 'shell', label: 'Shell' },
                { value: 'browser', label: 'Browser' },
                { value: 'editor', label: 'Editor' },
                { value: 'git', label: 'Git' },
                { value: 'database', label: 'Database' },
              ]}
            />
          </Col>
          <Col>
            <Select
              placeholder="Decision"
              value={filterPolicyDecision}
              onChange={setFilterPolicyDecision}
              allowClear
              style={{ width: 120 }}
              options={[
                { value: 'allow', label: 'Allow' },
                { value: 'deny', label: 'Deny' },
                { value: 'warn', label: 'Warn' },
                { value: 'audit', label: 'Audit' },
              ]}
            />
          </Col>
          <Col>
            <RangePicker
              showTime
              onChange={(_, dateStrings) => {
                setFilterDateFrom(dateStrings[0] || undefined);
                setFilterDateTo(dateStrings[1] || undefined);
              }}
            />
          </Col>
          <Col>
            <Space>
              <Button type="primary" icon={<SearchOutlined />} onClick={handleSearch}>
                Search
              </Button>
              <Button icon={<ReloadOutlined />} onClick={handleClearFilters}>
                Clear
              </Button>
            </Space>
          </Col>
        </Row>
      </Card>

      {/* Events table */}
      <Card size="small">
        <Table<Event>
          columns={columns}
          dataSource={events}
          rowKey="event_id"
          loading={loading}
          pagination={false}
          size="small"
          scroll={{ x: 1400 }}
          onRow={(record) => ({
            onClick: () => handleRowClick(record),
            style: {
              cursor: 'pointer',
              ...(highlightedIds.has(record.event_id)
                ? {
                    animation: 'eventHighlight 3s ease-out',
                    backgroundColor: '#fffbe6',
                  }
                : {}),
            },
          })}
        />
        {hasMore && (
          <div style={{ textAlign: 'center', marginTop: 16 }}>
            <Button
              type="dashed"
              loading={loading}
              onClick={handleLoadMore}
              icon={<ExportOutlined />}
              block
            >
              Load More
            </Button>
          </div>
        )}
      </Card>

      {/* Highlight animation style */}
      <style>{`
        @keyframes eventHighlight {
          0%   { background-color: #fffbe6; }
          100% { background-color: transparent; }
        }
      `}</style>

      {/* Event detail modal */}
      <Modal
        title={selectedEvent ? `Event: ${selectedEvent.event_id}` : 'Event Detail'}
        open={detailOpen}
        onCancel={handleCloseDetail}
        width={720}
        footer={[
          <Button key="close" onClick={handleCloseDetail}>Close</Button>,
        ]}
      >
        {selectedEvent && (
          <Descriptions column={2} size="small" bordered>
            <Descriptions.Item label="Event ID" span={2}>
              {selectedEvent.event_id}
            </Descriptions.Item>
            <Descriptions.Item label="Event Type">
              {selectedEvent.event_type}
            </Descriptions.Item>
            <Descriptions.Item label="Timestamp">
              {formatTimestamp(selectedEvent.timestamp)}
            </Descriptions.Item>
            <Descriptions.Item label="Device ID">
              {selectedEvent.device_id}
            </Descriptions.Item>
            <Descriptions.Item label="Hostname">
              {selectedEvent.hostname ?? '-'}
            </Descriptions.Item>
            <Descriptions.Item label="User ID">
              {selectedEvent.user_id ?? '-'}
            </Descriptions.Item>
            <Descriptions.Item label="Session ID">
              {selectedEvent.session_id ?? '-'}
            </Descriptions.Item>
            <Descriptions.Item label="Agent ID">
              {selectedEvent.agent_id ?? '-'}
            </Descriptions.Item>
            <Descriptions.Item label="Run ID">
              {selectedEvent.run_id ?? '-'}
            </Descriptions.Item>
            <Descriptions.Item label="Tool Name">
              {selectedEvent.tool_name ?? '-'}
            </Descriptions.Item>
            <Descriptions.Item label="Tool Category">
              {selectedEvent.tool_category ?? '-'}
            </Descriptions.Item>
            <Descriptions.Item label="Input Provenance">
              {selectedEvent.input_provenance ?? '-'}
            </Descriptions.Item>
            <Descriptions.Item label="Risk Score">
              <span style={{
                fontWeight: 600,
                color: selectedEvent.risk_score >= 80 ? 'red'
                  : selectedEvent.risk_score >= 50 ? 'orange'
                  : 'green',
              }}>
                {selectedEvent.risk_score}
              </span>
            </Descriptions.Item>
            <Descriptions.Item label="Severity">
              <Tag color={SEVERITY_COLORS[selectedEvent.severity ?? ''] ?? 'default'}>
                {(selectedEvent.severity ?? '-').toUpperCase()}
              </Tag>
            </Descriptions.Item>
            <Descriptions.Item label="Policy Decision">
              {selectedEvent.policy_decision ? (
                <Tag color={DECISION_COLORS[selectedEvent.policy_decision] ?? 'default'}>
                  {selectedEvent.policy_decision.toUpperCase()}
                </Tag>
              ) : '-'}
            </Descriptions.Item>
            <Descriptions.Item label="Policy ID">
              {selectedEvent.policy_id ?? '-'}
            </Descriptions.Item>
            <Descriptions.Item label="Policy Version">
              {selectedEvent.policy_version ?? '-'}
            </Descriptions.Item>
            <Descriptions.Item label="Params Summary" span={2}>
              <Tooltip title={selectedEvent.params_summary}>
                <span style={{ wordBreak: 'break-all' }}>
                  {selectedEvent.params_summary ?? '-'}
                </span>
              </Tooltip>
            </Descriptions.Item>
            <Descriptions.Item label="Risk Labels" span={2}>
              {selectedEvent.risk_labels_json && selectedEvent.risk_labels_json.length > 0
                ? selectedEvent.risk_labels_json.map((label: string) => (
                    <Tag key={label} color="orange" style={{ marginBottom: 4 }}>{label}</Tag>
                  ))
                : '-'}
            </Descriptions.Item>
            <Descriptions.Item label="Reason" span={2}>
              {selectedEvent.reason ?? '-'}
            </Descriptions.Item>
            <Descriptions.Item label="Params (Redacted JSON)" span={2}>
              <pre style={{
                maxHeight: 300,
                overflow: 'auto',
                background: '#f5f5f5',
                padding: 12,
                borderRadius: 4,
                fontSize: 12,
                lineHeight: 1.5,
                fontFamily: 'ui-monospace, Consolas, monospace',
                margin: 0,
              }}>
                {JSON.stringify(selectedEvent.params_redacted_json ?? {}, null, 2)}
              </pre>
            </Descriptions.Item>
            <Descriptions.Item label="Content Uploaded">
              {selectedEvent.content_uploaded ? 'Yes' : 'No'}
            </Descriptions.Item>
            <Descriptions.Item label="Created At">
              {formatTimestamp(selectedEvent.created_at)}
            </Descriptions.Item>
          </Descriptions>
        )}
      </Modal>
    </div>
  );
}
