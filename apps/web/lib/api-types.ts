export type AnalysisComment = {
  id: string;
  text: string;
  username: string | null;
  like_count: number;
  similarity: number;
};

export type AnalysisCluster = {
  id: string;
  rank: number;
  label: string;
  canonical_question: string;
  opportunity_score: number;
  mention_count: number;
  total_likes: number;
  signal: string;
  comments: AnalysisComment[];
};

export type AnalysisResult = {
  id: string;
  import_id: string;
  status: string;
  provider: string;
  comment_count: number;
  created_at: string;
  completed_at: string | null;
  clusters: AnalysisCluster[];
};

export type UsageResponse = {
  month: string;
  comments: { used: number; limit: number; remaining: number };
  analyses: { used: number; limit: number; remaining: number };
  generations: { used: number; limit: number; remaining: number };
};

export type InstagramAccount = {
  connected: boolean;
  username: string | null;
  instagram_user_id: string | null;
  account_type: string | null;
  connected_at: string | null;
};

export type ContentLanguage = "English" | "Hindi" | "Hinglish";
export type ContentTone = "Educational" | "Conversational" | "Energetic" | "Storytelling";

export type ContentPack = {
  id: string;
  cluster_id: string;
  version: number;
  status: string;
  provider: string;
  model: string;
  prompt_version: string;
  language: ContentLanguage;
  tone: ContentTone;
  hooks: string[];
  script_15: string;
  script_30: string;
  script_60: string;
  caption: string;
  cta: string;
  hashtags: string[];
  cover_text: string;
  b_roll: string[];
  input_tokens: number | null;
  output_tokens: number | null;
  created_at: string;
  updated_at: string;
};
