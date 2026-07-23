export type ExampleMetric = {
  label: string;
  value: string;
};

export type ExampleProject = {
  slug: string;
  name: string;
  ownerPersona: string;
  description: string;
  datasetName: string;
  datasetShape: string;
  featureSetName: string;
  modelName: string;
  modelType: string;
  objectiveMetric: string;
  endpointPath: string;
  alertSignal: string;
  retrainingPolicy: string;
  metrics: ExampleMetric[];
  lifecycleStages: string[];
};

export const exampleProjects: ExampleProject[] = [
  {
    slug: "movie-recommendation",
    name: "Movie Recommendation",
    ownerPersona: "Personalization ML engineer",
    description: "Ranking workflow for personalized movie recommendations.",
    datasetName: "Movie Ratings Interactions",
    datasetShape: "CSV interactions with member, title, rating, genre, and watch-time fields",
    featureSetName: "Member Movie Ranking Features",
    modelName: "Movie Candidate Ranker",
    modelType: "PyTorch two-tower ranker",
    objectiveMetric: "ndcg_at_10",
    endpointPath: "/inference/movie-ranking",
    alertSignal: "P95 latency over 150 ms",
    retrainingPolicy: "Drift-triggered retraining with approval",
    metrics: [
      { label: "NDCG@10", value: "0.418" },
      { label: "MAP@10", value: "0.291" },
      { label: "Coverage", value: "83%" }
    ],
    lifecycleStages: [
      "dataset version",
      "feature pipeline",
      "experiment",
      "approved model",
      "deployment",
      "drift policy"
    ]
  },
  {
    slug: "semantic-search",
    name: "Semantic Search",
    ownerPersona: "Search and retrieval ML engineer",
    description: "Dense retrieval workflow for searchable platform documentation.",
    datasetName: "Knowledge Base Documents",
    datasetShape: "JSONL document chunks with title, body, category, timestamp, and language",
    featureSetName: "Document Retrieval Features",
    modelName: "Knowledge Base Retriever",
    modelType: "Sentence-transformer embedding model",
    objectiveMetric: "recall_at_5",
    endpointPath: "/inference/semantic-search",
    alertSignal: "Inference error rate over 2%",
    retrainingPolicy: "Query drift-triggered embedding refresh",
    metrics: [
      { label: "Recall@5", value: "0.872" },
      { label: "MRR@10", value: "0.641" },
      { label: "Coverage", value: "100%" }
    ],
    lifecycleStages: [
      "dataset version",
      "embedding pipeline",
      "experiment",
      "approved model",
      "deployment",
      "drift policy"
    ]
  },
  {
    slug: "fraud-detection",
    name: "Fraud Detection",
    ownerPersona: "Risk ML engineer",
    description: "Online card transaction fraud scoring workflow.",
    datasetName: "Card Transaction Events",
    datasetShape: "CSV transactions with account, merchant, country, amount, and label fields",
    featureSetName: "Transaction Risk Features",
    modelName: "Transaction Fraud Scorer",
    modelType: "XGBoost classifier",
    objectiveMetric: "auc",
    endpointPath: "/inference/fraud-scoring",
    alertSignal: "Inference error rate over 1%",
    retrainingPolicy: "Risk-feature drift retraining with approval",
    metrics: [
      { label: "AUC", value: "0.947" },
      { label: "Precision@1%", value: "0.412" },
      { label: "Recall@5%", value: "0.781" }
    ],
    lifecycleStages: [
      "dataset version",
      "feature pipeline",
      "experiment",
      "approved model",
      "deployment",
      "drift policy"
    ]
  }
];
