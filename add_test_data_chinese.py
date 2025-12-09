import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_ANON_KEY"))

# 测试数据 - 使用中文列名
test_cases = [
    {
        "案号": "(2018)沪72协外认7号",
        "审理法院": "上海海事法院",
        "裁判日期": "2018-05-20T00:00:00+00:00",  # 注意时间格式
        "案件类型": "民事",
        "裁判理由": "涉外仲裁裁决承认与执行案例"
    },
    {
        "案号": "(2019)沪72民初123号",
        "审理法院": "上海海事法院", 
        "裁判日期": "2019-08-15T00:00:00+00:00",
        "案件类型": "民事",
        "裁判理由": "海上货物运输合同纠纷"
    },
    {
        "案号": "(2020)沪72行初45号",
        "审理法院": "上海海事法院",
        "裁判日期": "2020-03-10T00:00:00+00:00", 
        "案件类型": "行政",
        "裁判理由": "海事行政处罚案件"
    }
]

# 插入数据
for case in test_cases:
    try:
        result = supabase.table("case1").insert(case).execute()
        if result.data:
            print(f"成功插入: {case['案号']}")
        else:
            print(f"插入失败: {case['案号']} - {result.error}")
    except Exception as e:
        print(f"错误: {e}")