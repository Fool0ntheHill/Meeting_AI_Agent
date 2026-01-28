import { Steps } from 'antd'

const stepItems = [{ title: '上传并排序' }, { title: '选择配置' }]

const CreateTaskSteps = ({ current }: { current: number }) => (
  <div className="create-task__steps">
    <Steps current={current} items={stepItems} />
  </div>
)

export default CreateTaskSteps
