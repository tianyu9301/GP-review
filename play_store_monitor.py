import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from google_play_scraper import app, reviews_all
import pandas as pd
import matplotlib.pyplot as plt
from collections import Counter
import re
import os
import json
import google.generativeai as genai

# Set Chinese font for matplotlib
plt.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'SimHei', 'STHeiti']
plt.rcParams['axes.unicode_minus'] = False

class PlayStoreMonitor:
    def __init__(self, app_id, gemini_api_key=None):
        """
        初始化监控器，输入Google Play应用ID
        示例: 'com.yg.mini.games'
        """
        self.app_id = app_id
        self.app_info = None
        self.last_update_date = None
        self.reviews_data = None
        self.gemini_api_key = gemini_api_key
        
    def get_last_update_date(self):
        """
        获取应用在Google Play商店的最后更新日期
        """
        try:
            # 获取应用信息
            self.app_info = app(self.app_id)
            self.last_update_date = self.app_info['updated']
            
            # 转换为datetime对象
            if isinstance(self.last_update_date, int):
                # 检查是毫秒（13位）还是秒（10位）
                if self.last_update_date > 10000000000:  # 可能是毫秒
                    self.last_update_date = datetime.fromtimestamp(self.last_update_date / 1000)
                else:  # 可能是秒
                    self.last_update_date = datetime.fromtimestamp(self.last_update_date)
            elif not isinstance(self.last_update_date, datetime):
                try:
                    self.last_update_date = datetime.fromisoformat(str(self.last_update_date))
                except:
                    print(f"警告：无法解析日期格式: {self.last_update_date}")
            
            print(f"应用名称: {self.app_info['title']}")
            print(f"最后更新: {self.last_update_date}")
            
            return self.last_update_date
            
        except Exception as e:
            print(f"获取应用信息时出错: {e}")
            return None
    
    def check_update_threshold(self, min_days=7, max_days=30):
        """
        检查应用更新是否在可接受范围内
        返回: 
            - 'proceed' 如果在min_days和max_days之间
            - 'too_recent' 如果小于min_days
            - 'too_old' 如果大于max_days
        """
        if not self.last_update_date:
            self.get_last_update_date()
        
        today = datetime.now()
        days_since_update = (today - self.last_update_date).days
        
        print(f"距上次更新天数: {days_since_update}")
        
        if days_since_update > max_days:
            print(f"❌ 应用已有{days_since_update}天未更新（超过{max_days}天阈值）")
            print(f"   跳过分析 - 应用可能已被放弃或过时")
            return 'too_old'
        elif days_since_update < min_days:
            print(f"✓ 应用最近刚更新（{days_since_update}天前，最小阈值：{min_days}天）")
            print(f"   跳过分析 - 时间不足")
            return 'too_recent'
        else:
            print(f"✓ 应用更新在可接受范围内（{days_since_update}天）")
            print(f"   开始分析...")
            return 'proceed'
    
    def get_reviews_since_update(self):
        """
        获取最后更新日期到今天之间的所有评论
        """
        if not self.last_update_date:
            self.get_last_update_date()
        
        print("\n正在获取评论... 这可能需要一些时间。")
        
        try:
            # 获取所有评论
            all_reviews = reviews_all(
                self.app_id,
                sleep_milliseconds=0,
                lang='en',
                country='us'
            )
            
            # 筛选更新后的评论
            filtered_reviews = []
            for review in all_reviews:
                review_date = review['at']
                if review_date >= self.last_update_date:
                    filtered_reviews.append(review)
            
            self.reviews_data = filtered_reviews
            print(f"找到{len(filtered_reviews)}条自上次更新以来的评论")
            
            return filtered_reviews
            
        except Exception as e:
            print(f"获取评论时出错: {e}")
            return []
    
    def analyze_reviews(self):
        """
        分析评论趋势并生成洞察
        """
        if not self.reviews_data:
            print("没有可用的评论数据。请先获取评论。")
            return None, None
        
        df = pd.DataFrame(self.reviews_data)
        
        # 基础统计
        analysis = {
            'total_reviews': len(df),
            'average_rating': df['score'].mean(),
            'rating_distribution': df['score'].value_counts().sort_index().to_dict(),
            'total_thumbs_up': df['thumbsUpCount'].sum(),
        }
        
        # 基于评分的情感分析
        df['sentiment'] = df['score'].apply(lambda x: 
            '正面' if x >= 4 else ('中性' if x == 3 else '负面'))
        
        analysis['sentiment_distribution'] = df['sentiment'].value_counts().to_dict()
        
        # 评论中的常见词汇（排除常见停用词）
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 
                      'of', 'with', 'is', 'was', 'are', 'been', 'be', 'have', 'has', 'had',
                      'this', 'that', 'it', 'i', 'my', 'me', 'you', 'your', 'app', 'game',
                      'very', 'really', 'just', 'like', 'get', 'got', 'can', 'cant', 'dont',
                      'will', 'would', 'could', 'should', 'much', 'more', 'most', 'many',
                      'some', 'also', 'only', 'from', 'when', 'there', 'they', 'them',
                      'than', 'then', 'these', 'those', 'what', 'which', 'who', 'where',
                      'why', 'how', 'all', 'each', 'every', 'both', 'few', 'more', 'other',
                      'such', 'own', 'same', 'than', 'too', 'even', 'well', 'without',
                      'good', 'great', 'nice', 'best', 'love', 'bad', 'hate', 'worst'}
        
        all_words = []
        for content in df['content'].dropna():
            words = re.findall(r'\b[a-z]+\b', content.lower())
            all_words.extend([w for w in words if w not in stop_words and len(w) > 3])
        
        analysis['top_keywords'] = dict(Counter(all_words).most_common(20))
        
        # 每日趋势
        df['date'] = pd.to_datetime(df['at']).dt.date
        daily_stats = df.groupby('date').agg({
            'score': ['mean', 'count']
        }).round(2)
        
        analysis['daily_trends'] = daily_stats.to_dict()
        
        return analysis, df
    
    def prepare_research_data(self, analysis, df):
        """
        准备提供给Gemini的研究数据
        """
        # 基础数据
        avg_rating = analysis['average_rating']
        total_reviews = analysis['total_reviews']
        negative_pct = analysis['sentiment_distribution'].get('负面', 0) / total_reviews * 100
        positive_pct = analysis['sentiment_distribution'].get('正面', 0) / total_reviews * 100
        neutral_pct = analysis['sentiment_distribution'].get('中性', 0) / total_reviews * 100
        days_analyzed = (datetime.now() - self.last_update_date).days
        
        # 收集代表性评论
        sample_reviews = {
            'positive': [],
            'negative': [],
            'neutral': []
        }
        
        # 正面评论样本
        positive_df = df[df['sentiment'] == '正面'].sort_values('thumbsUpCount', ascending=False)
        for _, row in positive_df.head(5).iterrows():
            sample_reviews['positive'].append({
                'content': str(row['content']),
                'score': int(row['score']),
                'thumbs_up': int(row['thumbsUpCount'])
            })
        
        # 负面评论样本
        negative_df = df[df['sentiment'] == '负面'].sort_values('thumbsUpCount', ascending=False)
        for _, row in negative_df.head(5).iterrows():
            sample_reviews['negative'].append({
                'content': str(row['content']),
                'score': int(row['score']),
                'thumbs_up': int(row['thumbsUpCount'])
            })
        
        # 中性评论样本
        neutral_df = df[df['sentiment'] == '中性'].sort_values('thumbsUpCount', ascending=False)
        for _, row in neutral_df.head(3).iterrows():
            sample_reviews['neutral'].append({
                'content': str(row['content']),
                'score': int(row['score']),
                'thumbs_up': int(row['thumbsUpCount'])
            })
        
        # 转换rating_distribution中的numpy int64为Python int
        rating_dist = {int(k): int(v) for k, v in analysis['rating_distribution'].items()}
        
        # 转换top_keywords
        top_keywords = {k: int(v) for k, v in analysis['top_keywords'].items()}
        
        # 每日趋势数据
        daily_counts = df.groupby('date').size().to_dict()
        daily_avg_rating = df.groupby('date')['score'].mean().to_dict()
        
        # 构建研究报告数据
        research_report = {
            'app_name': self.app_info['title'],
            'app_id': self.app_id,
            'version': self.app_info.get('version', 'N/A'),
            'last_update_date': self.last_update_date.strftime('%Y年%m月%d日'),
            'analysis_period_days': int(days_analyzed),
            'statistics': {
                'total_reviews': int(total_reviews),
                'average_rating': round(float(avg_rating), 2),
                'positive_percentage': round(float(positive_pct), 1),
                'negative_percentage': round(float(negative_pct), 1),
                'neutral_percentage': round(float(neutral_pct), 1),
                'rating_distribution': rating_dist,
                'total_thumbs_up': int(analysis['total_thumbs_up'])
            },
            'top_keywords': top_keywords,
            'sample_reviews': sample_reviews,
            'daily_trends': {
                'review_counts': {str(k): int(v) for k, v in daily_counts.items()},
                'average_ratings': {str(k): round(float(v), 2) for k, v in daily_avg_rating.items()}
            }
        }
        
        return research_report
    
    def call_gemini_api(self, research_data):
        """
        调用Gemini API生成Newsletter
        """
        if not self.gemini_api_key:
            print("❌ 未配置Gemini API Key")
            return None
        
        try:
            # 配置Gemini
            genai.configure(api_key=self.gemini_api_key)
            
            # 使用Gemini 2.5 Flash（最新且快速的模型）
            model = genai.GenerativeModel('models/gemini-2.5-flash')
            print(f"✓ 使用模型: gemini-2.5-flash")
            
            # 构建Prompt（精简版）
            prompt = f"""You are a professor of marketing research. From the input, generate 3-5 sentences on the trend of the Google Play reviews, focusing on bugs and product feedbacks.

App: {research_data['app_name']}
Last Update: {research_data['last_update_date']}
Analysis Period: {research_data['analysis_period_days']} days

Statistics:
- Total Reviews: {research_data['statistics']['total_reviews']}
- Average Rating: {research_data['statistics']['average_rating']}/5.0
- Positive: {research_data['statistics']['positive_percentage']}%
- Negative: {research_data['statistics']['negative_percentage']}%

Top Keywords: {', '.join(list(research_data['top_keywords'].keys())[:10])}

Sample Negative Reviews (focus on bugs/issues):
{json.dumps(research_data['sample_reviews']['negative'], ensure_ascii=False, indent=2)}

Sample Positive Reviews (focus on features users like):
{json.dumps(research_data['sample_reviews']['positive'], ensure_ascii=False, indent=2)}

Output in Chinese, 3-5 sentences analyzing the main bugs, feature requests, and product feedback trends."""
            
            # 调用API
            response = model.generate_content(prompt)
            
            if response and response.text:
                print("✓ Gemini AI分析完成")
                return response.text
            else:
                print("❌ Gemini返回空响应")
                return None
                
        except Exception as e:
            print(f"❌ Gemini API调用出错: {e}")
            return None
    
    def generate_strategic_newsletter(self, analysis, df, output_file=None):
        """
        使用Gemini API生成战略性Newsletter（精简版，聚焦bug和产品反馈）
        """
        if output_file is None:
            safe_app_id = self.app_id.replace('.', '_')
            timestamp = datetime.now().strftime('%Y%m%d')
            output_file = f'{safe_app_id}_newsletter_{timestamp}.md'
        
        print("\n正在使用Gemini AI生成专业分析报告...")
        
        # 准备给Gemini的数据摘要
        research_data = self.prepare_research_data(analysis, df)
        
        # 调用Gemini API生成分析
        gemini_analysis = self.call_gemini_api(research_data)
        
        # 构建完整Newsletter
        newsletter = []
        
        # 邮件主题
        update_date = self.last_update_date.strftime('%Y年%m月%d日')
        app_name = self.app_info['title']
        newsletter.append(f"**邮件主题:** Google Play 更新舆情监控：{update_date} - {app_name}\n")
        newsletter.append("---\n\n")
        
        if gemini_analysis:
            # 使用Gemini生成的分析
            newsletter.append("## AI 分析报告\n\n")
            newsletter.append(gemini_analysis)
            newsletter.append("\n\n---\n\n")
        
        # 添加数据摘要
        newsletter.append("## 数据摘要\n\n")
        newsletter.append(f"**分析周期:** 更新后 {research_data['analysis_period_days']} 天\n")
        newsletter.append(f"**总评论数:** {research_data['statistics']['total_reviews']}\n")
        newsletter.append(f"**平均评分:** {research_data['statistics']['average_rating']}/5.0\n")
        newsletter.append(f"**情感分布:** 正面 {research_data['statistics']['positive_percentage']}% | ")
        newsletter.append(f"中性 {research_data['statistics']['neutral_percentage']}% | ")
        newsletter.append(f"负面 {research_data['statistics']['negative_percentage']}%\n\n")
        
        # 高频关键词
        newsletter.append("**高频关键词:**\n")
        for keyword, count in list(research_data['top_keywords'].items())[:10]:
            newsletter.append(f"- {keyword}: {count}次\n")
        
        newsletter.append("\n---\n\n")
        newsletter.append("如有问题或建议请随时联系。\n")
        
        # 写入文件
        newsletter_text = "".join(newsletter)
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(newsletter_text)
        
        print(f"\n✓ Newsletter已保存至 {output_file}")
        return newsletter_text, output_file
    
    def create_visualizations(self, output_file=None):
        """
        创建可视化图表
        """
        if output_file is None:
            safe_app_id = self.app_id.replace('.', '_')
            output_file = f'{safe_app_id}_charts.png'
        
        if not self.reviews_data:
            print("没有可用的评论数据。")
            return None
        
        df = pd.DataFrame(self.reviews_data)
        df['date'] = pd.to_datetime(df['at']).dt.date
        
        fig, axes = plt.subplots(2, 2, figsize=(15, 10))
        fig.suptitle(f'评论分析: {self.app_info["title"]}', fontsize=16, fontweight='bold')
        
        # 1. 评分分布
        rating_counts = df['score'].value_counts().sort_index()
        axes[0, 0].bar(rating_counts.index, rating_counts.values, color='skyblue', edgecolor='navy')
        axes[0, 0].set_title('评分分布', fontsize=12, fontweight='bold')
        axes[0, 0].set_xlabel('评分')
        axes[0, 0].set_ylabel('数量')
        axes[0, 0].set_xticks([1, 2, 3, 4, 5])
        axes[0, 0].grid(axis='y', alpha=0.3)
        
        # 2. 每日评论量趋势
        daily_counts = df.groupby('date').size()
        axes[0, 1].plot(daily_counts.index, daily_counts.values, marker='o', color='green', linewidth=2)
        axes[0, 1].fill_between(daily_counts.index, daily_counts.values, alpha=0.3, color='green')
        axes[0, 1].set_title('每日评论量', fontsize=12, fontweight='bold')
        axes[0, 1].set_xlabel('日期')
        axes[0, 1].set_ylabel('评论数')
        axes[0, 1].tick_params(axis='x', rotation=45)
        axes[0, 1].grid(alpha=0.3)
        
        # 3. 每日平均评分趋势
        daily_avg = df.groupby('date')['score'].mean()
        axes[1, 0].plot(daily_avg.index, daily_avg.values, marker='o', color='orange', linewidth=2)
        axes[1, 0].set_title('每日平均评分', fontsize=12, fontweight='bold')
        axes[1, 0].set_xlabel('日期')
        axes[1, 0].set_ylabel('平均评分')
        axes[1, 0].set_ylim([0, 5])
        axes[1, 0].axhline(y=3.5, color='r', linestyle='--', label='3.5阈值', linewidth=2)
        axes[1, 0].legend()
        axes[1, 0].tick_params(axis='x', rotation=45)
        axes[1, 0].grid(alpha=0.3)
        
        # 4. 情感饼图
        df['sentiment'] = df['score'].apply(lambda x: 
            '正面' if x >= 4 else ('中性' if x == 3 else '负面'))
        sentiment_counts = df['sentiment'].value_counts()
        colors = {'正面': 'lightgreen', '中性': 'yellow', '负面': 'lightcoral'}
        axes[1, 1].pie(sentiment_counts.values, labels=sentiment_counts.index, autopct='%1.1f%%',
                       colors=[colors.get(x, 'gray') for x in sentiment_counts.index],
                       startangle=90, textprops={'fontsize': 11})
        axes[1, 1].set_title('情感分布', fontsize=12, fontweight='bold')
        
        plt.tight_layout()
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        print(f"✓ 可视化图表已保存至 {output_file}")
        plt.close()
        
        return output_file
    
    def run_full_analysis(self, min_days=7, max_days=30):
        """
        运行完整分析流程
        返回: 分析状态 ('success', 'too_recent', 'too_old', 'error')
        """
        print(f"\n{'='*80}")
        print(f"正在分析: {self.app_id}")
        print("=" * 80)
        
        try:
            # 步骤1: 获取最后更新日期
            if not self.get_last_update_date():
                print("❌ 获取应用信息失败")
                return 'error'
            
            # 步骤2: 检查更新是否在可接受范围内
            status = self.check_update_threshold(min_days, max_days)
            
            if status != 'proceed':
                return status
            
            # 步骤3: 获取更新后的评论
            self.get_reviews_since_update()
            
            if not self.reviews_data or len(self.reviews_data) == 0:
                print("\n⚠️  在指定期间内未找到评论。")
                return 'no_reviews'
            
            # 步骤4: 分析评论
            analysis, df = self.analyze_reviews()
            
            if not analysis:
                return 'error'
            
            # 步骤5: 生成Newsletter
            newsletter_text, newsletter_file = self.generate_strategic_newsletter(analysis, df)
            print(f"📄 Newsletter: {newsletter_file}")
            
            # 步骤6: 生成可视化
            viz_file = self.create_visualizations()
            if viz_file:
                print(f"📊 图表: {viz_file}")
            
            return 'success'
            
        except Exception as e:
            print(f"❌ 分析过程中出错: {e}")
            import traceback
            traceback.print_exc()
            return 'error'


class MultiAppMonitor:
    """
    监控多个应用
    """
    def __init__(self, gemini_api_key=None):
        self.app_ids = []
        self.results = {}
        self.gemini_api_key = gemini_api_key
        
    def prompt_for_apps(self):
        """
        提示用户输入应用ID
        """
        print("\n" + "="*80)
        print("GOOGLE PLAY 商店 - 多应用舆情分析系统")
        print("="*80)
        print("\n请输入要分析的Google Play应用ID。")
        print("您可以输入:")
        print("  - 单个应用ID: com.example.app")
        print("  - 用逗号分隔的多个ID: com.app1,com.app2,com.app3")
        print("  - 用空格分隔的多个ID: com.app1 com.app2 com.app3")
        print("  - 输入'file'从文件加载")
        print("  - 在空行按回车完成输入\n")
        
        app_ids = []
        
        while True:
            user_input = input("输入应用ID或'file': ").strip()
            
            if not user_input:
                break
            
            if user_input.lower() == 'file':
                file_path = input("输入文件路径（每行一个应用ID）: ").strip()
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        file_ids = [line.strip() for line in f if line.strip()]
                        app_ids.extend(file_ids)
                        print(f"✓ 从文件加载了{len(file_ids)}个应用ID")
                except Exception as e:
                    print(f"❌ 读取文件时出错: {e}")
                continue
            
            # 处理逗号或空格分隔的ID
            if ',' in user_input:
                ids = [id.strip() for id in user_input.split(',') if id.strip()]
            elif ' ' in user_input:
                ids = [id.strip() for id in user_input.split() if id.strip()]
            else:
                ids = [user_input]
            
            app_ids.extend(ids)
            print(f"✓ 已添加{len(ids)}个应用ID。总计: {len(app_ids)}")
        
        if not app_ids:
            print("\n❌ 未提供应用ID。退出程序。")
            return False
        
        # 去重但保持顺序
        self.app_ids = list(dict.fromkeys(app_ids))
        
        print(f"\n📱 将分析{len(self.app_ids)}个应用:")
        for i, app_id in enumerate(self.app_ids, 1):
            print(f"   {i}. {app_id}")
        
        return True
    
    def analyze_all_apps(self, min_days=7, max_days=30):
        """
        分析列表中的所有应用
        """
        if not self.app_ids:
            print("没有要分析的应用")
            return
        
        print(f"\n{'='*80}")
        print(f"开始批量分析")
        print(f"最小更新天数: {min_days}")
        print(f"最大更新天数: {max_days}")
        print("="*80)
        
        for i, app_id in enumerate(self.app_ids, 1):
            print(f"\n\n[{i}/{len(self.app_ids)}] 正在处理: {app_id}")
            
            monitor = PlayStoreMonitor(app_id, gemini_api_key=self.gemini_api_key)
            status = monitor.run_full_analysis(min_days, max_days)
            
            self.results[app_id] = {
                'status': status,
                'app_name': monitor.app_info.get('title', '未知') if monitor.app_info else '未知',
                'last_update': monitor.last_update_date
            }
        
        self.generate_summary_report()
    
    def generate_summary_report(self):
        """
        生成所有应用的汇总报告
        """
        print("\n\n" + "="*80)
        print("批量分析汇总")
        print("="*80)
        
        summary = {
            'success': [],
            'too_recent': [],
            'too_old': [],
            'no_reviews': [],
            'error': []
        }
        
        for app_id, result in self.results.items():
            summary[result['status']].append({
                'id': app_id,
                'name': result['app_name'],
                'date': result['last_update']
            })
        
        print(f"\n✅ 成功分析: {len(summary['success'])}")
        for app in summary['success']:
            print(f"   • {app['name']} ({app['id']})")
        
        print(f"\n⏭️  跳过（更新太近）: {len(summary['too_recent'])}")
        for app in summary['too_recent']:
            print(f"   • {app['name']} ({app['id']})")
        
        print(f"\n❌ 跳过（更新超过30天）: {len(summary['too_old'])}")
        for app in summary['too_old']:
            days_old = (datetime.now() - app['date']).days if app['date'] else '未知'
            print(f"   • {app['name']} ({app['id']}) - {days_old}天前更新")
        
        print(f"\n⚠️  未找到评论: {len(summary['no_reviews'])}")
        for app in summary['no_reviews']:
            print(f"   • {app['name']} ({app['id']})")
        
        print(f"\n❌ 错误: {len(summary['error'])}")
        for app in summary['error']:
            print(f"   • {app['name']} ({app['id']})")
        
        # 保存汇总到文件
        summary_file = f"batch_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        with open(summary_file, 'w', encoding='utf-8') as f:
            f.write("="*80 + "\n")
            f.write("批量分析汇总\n")
            f.write("="*80 + "\n")
            f.write(f"分析日期: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"应用总数: {len(self.results)}\n\n")
            
            for status, apps in summary.items():
                status_name = {
                    'success': '成功分析',
                    'too_recent': '跳过（更新太近）',
                    'too_old': '跳过（超过30天）',
                    'no_reviews': '未找到评论',
                    'error': '错误'
                }.get(status, status.upper())
                
                f.write(f"\n{status_name}: {len(apps)}\n")
                f.write("-"*40 + "\n")
                for app in apps:
                    f.write(f"  {app['name']}\n")
                    f.write(f"  ID: {app['id']}\n")
                    if app['date']:
                        f.write(f"  最后更新: {app['date'].strftime('%Y-%m-%d')}\n")
                    f.write("\n")
        
        print(f"\n📄 汇总已保存至: {summary_file}")
        print("\n" + "="*80)


# 主程序执行
if __name__ == "__main__":
    # 提示用户输入Gemini API Key
    print("\n" + "="*80)
    print("欢迎使用 Google Play 舆情分析系统")
    print("="*80)
    print("\n此系统使用Gemini AI生成专业的分析报告。")
    
    api_key_input = input("\n请输入您的Gemini API Key（留空则跳过AI分析）: ").strip()
    
    if api_key_input:
        gemini_api_key = api_key_input
        print("✓ 已配置Gemini API，将使用AI生成专业报告")
    else:
        gemini_api_key = None
        print("⚠️  未配置API Key，将仅生成数据摘要")
    
    # 创建多应用监控器，传入API Key
    multi_monitor = MultiAppMonitor(gemini_api_key=gemini_api_key)
    
    # 提示用户输入应用ID
    if multi_monitor.prompt_for_apps():
        # 分析所有应用（最小7天，最大30天）
        multi_monitor.analyze_all_apps(min_days=7, max_days=30)
    
    print("\n✅ 全部完成！")
