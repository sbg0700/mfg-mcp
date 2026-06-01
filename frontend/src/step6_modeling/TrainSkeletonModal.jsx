// 학습 골격 모달 — STEP 3에서 실제 ML 학습 엔진 도입 예정.
// 우리 1B-3c 범위는 "추천(LLM)까지". 학습은 안내만.
export default function TrainSkeletonModal({ model, onClose }) {
  if (!model) return null
  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <h2>학습 시작 — 골격</h2>
        <p>
          선택한 모델 <strong>{model.name}</strong> (fit_score {model.fit_score}/5,
          task: {model.task})의 학습은
          <strong> STEP 3</strong>에서 실데이터 기반 실제 ML 엔진(RandomForest/XGBoost/IsolationForest fit)
          으로 실행됩니다.
        </p>
        <p className="muted">
          현재 1B-3c 범위는 "AggregatedContext → LLM 모델 추천(fit_score 1~5)"까지입니다.
          실 train 엔드포인트와 모델 저장/지표 산출은 후속 STEP에서 도입.
        </p>
        <div className="modal-actions">
          <button className="btn" onClick={onClose}>닫기</button>
        </div>
      </div>
    </div>
  )
}
