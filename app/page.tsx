import { supabase } from '@/lib/supabase';

export default async function Home() {
  const { data: cases, error } = await supabase
    .from('case1')       // 表名：必须完全一致
    .select('*')
    .limit(50);

  if (error) {
    return <div>数据库读取失败：{error.message}</div>;
  }

  return (
    <div style={{ padding: 20 }}>
      <h1 style={{ fontSize: '24px', marginBottom: '20px' }}>
        案例列表
      </h1>

      <ul>
        {cases?.map((c: any) => (
          <li key={c.id} style={{ marginBottom: '12px' }}>
            <strong>{c.案号}</strong>
            <div>{c.审理法院}</div>
            <div>{c.裁判日期}</div>
          </li>
        ))}
      </ul>
    </div>
  );
}

