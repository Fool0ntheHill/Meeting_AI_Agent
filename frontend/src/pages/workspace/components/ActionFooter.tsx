import { Button, Checkbox, Tooltip, Typography } from 'antd'
import { CheckCircleOutlined, CopyOutlined } from '@ant-design/icons'

interface ActionFooterProps {
  isConfirmed: boolean
  onConfirmChange: (checked: boolean) => void
  onCopy: () => void
  allowTrain: boolean
  onAllowTrainChange: (checked: boolean) => void
}

const ActionFooter = ({
  isConfirmed,
  onConfirmChange,
  onCopy,
  allowTrain,
  onAllowTrainChange
}: ActionFooterProps) => {
  return (
    <div className="workspace-footer">
      <div className="workspace-footer__content">
        <div className="workspace-footer__meta">
          <div className="workspace-footer__checkbox-row">
            <Checkbox
              checked={allowTrain}
              onChange={(e) => onAllowTrainChange(e.target.checked)}
              className="workspace-footer__checkbox"
            >
              <Typography.Text type="secondary" className="workspace-footer__text">
                允许 AI 学习本次修正以提升下次准确率
              </Typography.Text>
            </Checkbox>
            <Tooltip title="该选项会将本次录音转写内容写入日志，勾选前请确认本次会议无敏感内容">
              <span className="workspace-footer__info">i</span>
            </Tooltip>
          </div>
          <Checkbox
            checked={isConfirmed}
            onChange={(e) => onConfirmChange(e.target.checked)}
            className={`workspace-footer__checkbox${isConfirmed ? ' is-confirmed' : ''}`}
          >
            已经完整阅读文档并确认关键内容无误
          </Checkbox>
        </div>
        <div className="workspace-footer__actions">
          <Tooltip title={!isConfirmed ? '请先确认内容无误' : ''}>
            <Button
              type="primary"
              icon={isConfirmed ? <CheckCircleOutlined /> : <CopyOutlined />}
              disabled={!isConfirmed}
              onClick={onCopy}
              size="large"
            >
              一键复制全部
            </Button>
          </Tooltip>
        </div>
      </div>
    </div>
  )
}

export default ActionFooter
