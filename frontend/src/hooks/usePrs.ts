import { useState, useEffect } from 'react';
import api from '../lib/api';

interface PullRequest {
  id: number;
  title: string;
  author: string;
  state: string;
  pr_number: number;
  risk_score: number;
  findings_count: number;
  created_at: string;
}

export function usePRs() {
  const [prs, setPRs] = useState<PullRequest[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.get('/prs').then((res) => {
      setPRs(res.data);
      setLoading(false);
    }).catch(() => setLoading(false));
  }, []);

  return { prs, loading };
}
