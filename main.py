"""
排班闹钟APP - 点选排班 + 一键生成闹钟
"""
import os
import sys

# Windows渲染设置（安卓不需要）
if os.name == 'nt':
    os.environ['KIVY_GL_BACKEND'] = 'angle_sdl2'

from kivy.app import App
from kivy.core.text import LabelBase
from kivy.uix.gridlayout import GridLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.spinner import Spinner
from kivy.clock import Clock
from kivy.core.window import Window
import json
import calendar
from datetime import date, datetime

# 注册中文字体
if os.name == 'nt':
    # Windows: 使用系统微软雅黑
    LabelBase.register(name='ChineseFont', fn_regular='C:/Windows/Fonts/msyh.ttc')
else:
    # 安卓: 使用打包进去的文泉驿微米黑
    font_path = os.path.join(os.path.dirname(__file__), 'chinese_font.ttc')
    if os.path.exists(font_path):
        LabelBase.register(name='ChineseFont', fn_regular=font_path)


class ShiftCalendar(BoxLayout):
    """
    核心控件：显示月历，点日期设置排班
    
    BoxLayout = 盒子布局，里面的东西可以竖着排或横着排
    """

    # 排班类型对应的颜色
    SHIFT_COLORS = {
        '':     [0.25, 0.25, 0.30, 1],  # 无排班 → 深灰
        '白班': [0.18, 0.55, 0.22, 1],  # 白班 → 柔和绿
        '晚班': [0.15, 0.38, 0.70, 1],  # 晚班 → 柔和蓝
        '休息': [0.48, 0.48, 0.52, 1],  # 休息 → 柔和灰
    }
    
    # 排班简称（显示在日期格子里）
    SHIFT_SHORT = {
        '白班': '白',
        '晚班': '晚',
        '休息': '休',
    }

    def __init__(self, **kwargs):
        super().__init__(orientation='vertical', **kwargs)
        # orientation='vertical' → 里面的控件从上往下排

        self.schedule = {}      # 排班数据：{ '2026-07-15': '白班', ... }
        self.current_date = date.today()   # 当前显示的月份
        
        # 闹钟时间设置（默认值）
        self.alarm_times = {
            '白班': '07:30',
            '晚班': '15:30',
        }
        
        # 数据文件：用 APP 私有目录（安卓兼容，可读写）
        self.data_file = os.path.join(
            App.get_running_app().user_data_dir, 'data.json')
        
        # 启动时读取之前保存的数据
        self._load_data()
        
        # 闹钟跟踪
        self.alarm_list = []     # 要响的闹钟列表：[("2026-07-15 07:30", "白班"), ...]
        self.fired_alarms = set()# 已经响过的闹钟，避免重复
        self.fired_dates = set() # 已经响过闹钟的日期，用于显示标记
        
        # 启动后台检查，每 30 秒看一次到点了没
        Clock.schedule_interval(self._check_alarms, 30)
        
        self._build_ui()        # 搭界面

    def _build_ui(self):
        """搭界面"""
        # ── 顶部导航栏：上月 | 年月 | 下月 | 今天 | 设置 ──
        nav = BoxLayout(size_hint_y=0.1, spacing=5, padding=5)

        self.btn_prev = Button(
            text='< 上月', font_name='ChineseFont', font_size='14sp',
            background_color=[0.2, 0.2, 0.25, 1],
            background_normal=''
        )
        self.btn_prev.bind(on_press=self._prev_month)
        
        self.lbl_month = Label(
            text='', font_name='ChineseFont', font_size='18sp',
            bold=True
        )
        
        self.btn_next = Button(
            text='下月 >', font_name='ChineseFont', font_size='14sp',
            background_color=[0.2, 0.2, 0.25, 1],
            background_normal=''
        )
        self.btn_next.bind(on_press=self._next_month)
        
        self.btn_today = Button(
            text='今天', font_name='ChineseFont', font_size='13sp',
            size_hint_x=0.2,
            background_color=[0.25, 0.25, 0.30, 1],
            background_normal=''
        )
        self.btn_today.bind(on_press=self._goto_today)
        
        self.btn_settings = Button(
            text='[ 设置 ]', font_name='ChineseFont', font_size='14sp',
            size_hint_x=0.2,
            background_color=[0.2, 0.2, 0.25, 1],
            background_normal=''
        )
        self.btn_settings.bind(on_press=self._open_settings)

        nav.add_widget(self.btn_prev)
        nav.add_widget(self.lbl_month)
        nav.add_widget(self.btn_next)
        nav.add_widget(self.btn_today)
        nav.add_widget(self.btn_settings)

        # ── 星期表头：日 一 二 三 四 五 六 ──
        header = GridLayout(cols=7, size_hint_y=0.08)
        for day_name in ['日', '一', '二', '三', '四', '五', '六']:
            header.add_widget(Label(
                text=day_name, font_name='ChineseFont', font_size='14sp',
                bold=True
            ))
        
        # ── 日期网格：7列，放这个月的所有日期按钮 ──
        self.date_grid = GridLayout(cols=7, spacing=2, padding=5)
        
        # 组装
        self.add_widget(nav)
        self.add_widget(header)
        self.add_widget(self.date_grid)
        
        # ── 本月统计栏 ──
        self.stats_label = Label(
            text='', font_name='ChineseFont', font_size='13sp',
            size_hint_y=0.06, color=[0.6, 0.6, 0.7, 1]
        )
        self.add_widget(self.stats_label)
        
        # 刷新日历
        self._refresh()
        
        # ── 底部：一键生成闹钟 ──
        bottom = BoxLayout(size_hint_y=0.1, spacing=10, padding=10)
        self.btn_gen = Button(
            text='[ 生成闹钟 ]',
            font_name='ChineseFont', font_size='14sp',
            background_color=[0.75, 0.40, 0.05, 1],  # 橙色
            background_normal=''
        )
        self.btn_gen.bind(on_press=self._generate_alarms)
        bottom.add_widget(self.btn_gen)
        
        self.btn_cancel = Button(
            text='[ 取消闹钟 ]',
            font_name='ChineseFont', font_size='14sp',
            background_color=[0.50, 0.15, 0.15, 1],  # 深红
            background_normal=''
        )
        self.btn_cancel.bind(on_press=self._cancel_alarms)
        bottom.add_widget(self.btn_cancel)
        
        self.btn_clear = Button(
            text='[ 清除排班 ]',
            font_name='ChineseFont', font_size='14sp',
            background_color=[0.30, 0.30, 0.35, 1],  # 灰色
            background_normal=''
        )
        self.btn_clear.bind(on_press=self._clear_schedule)
        bottom.add_widget(self.btn_clear)
        
        self.add_widget(bottom)

    def _refresh(self):
        """刷新日历：根据当前月份，重新画日期格子"""
        self.date_grid.clear_widgets()  # 清空旧的日期按钮
        
        year = self.current_date.year
        month = self.current_date.month
        
        # 更新顶部文字：如 "2026年7月"
        self.lbl_month.text = f'{year}年{month}月'
        
        # calendar.monthrange(年, 月) → 返回（1号星期几, 本月天数）
        # 星期：0=周一, 1=周二 ... 6=周日
        first_weekday, days_in_month = calendar.monthrange(year, month)
        
        # ── 填充空白格子 ──
        # 如果1号是周三（first_weekday=2），前面要空2格（日、一、二 → 周二才是1号）
        # 但calendar模块里 0=周一，而我们表头是 日=0，所以要转一下
        # 简单处理：周日=0, 周一=1 ... 周六=6
        weekday_sunday = (first_weekday + 1) % 7  # 转成周日开头
        for _ in range(weekday_sunday):
            self.date_grid.add_widget(Label())  # 空白占位
        
        # ── 填充日期按钮 ──
        for day in range(1, days_in_month + 1):
            date_key = f'{year}-{month:02d}-{day:02d}'  # 如 "2026-07-15"
            shift = self.schedule.get(date_key, '')       # 这天有没有排班？
            
            # 生成按钮文字：数字 + 班次简称 + 已响标记
            btn_text = str(day)
            if shift:
                btn_text = f'{day} {self.SHIFT_SHORT.get(shift, "")}'
            if date_key in self.fired_dates:
                btn_text += ' OK'
            
            btn = Button(
                text=btn_text,
                font_name='ChineseFont',
                font_size='16sp',
                background_color=self.SHIFT_COLORS.get(shift, self.SHIFT_COLORS['']),
                color=[1, 1, 1, 1] if shift else [0.8, 0.8, 0.8, 1]
            )
            # 把日期存到按钮上，方便点击时知道是哪天
            btn.date_key = date_key
            btn.bind(on_press=self._on_date_click)
            
            self.date_grid.add_widget(btn)
        
        # 补全最后一行的空格（保持网格整齐）
        total_cells = weekday_sunday + days_in_month
        remaining = (7 - total_cells % 7) % 7
        for _ in range(remaining):
            self.date_grid.add_widget(Label())
        
        # 更新本月统计
        self._update_stats()

    def _update_stats(self):
        """统计本月排班：白班X天 晚班X天 休X天"""
        year = self.current_date.year
        month = self.current_date.month
        prefix = f'{year}-{month:02d}'
        
        day_count = 0   # 白班
        night_count = 0 # 晚班
        rest_count = 0  # 休息
        
        for date_key, shift_type in self.schedule.items():
            if date_key.startswith(prefix):
                if shift_type == '白班':
                    day_count += 1
                elif shift_type == '晚班':
                    night_count += 1
                elif shift_type == '休息':
                    rest_count += 1
        
        self.stats_label.text = (
            f'本月：白班 {day_count}天  晚班 {night_count}天  '
            f'休息 {rest_count}天  共 {day_count + night_count}个工作日'
        )

    def _prev_month(self, instance):
        """上个月"""
        year = self.current_date.year
        month = self.current_date.month - 1
        if month == 0:
            month = 12
            year -= 1
        self.current_date = date(year, month, 1)
        self._refresh()

    def _next_month(self, instance):
        """下个月"""
        year = self.current_date.year
        month = self.current_date.month + 1
        if month == 13:
            month = 1
            year += 1
        self.current_date = date(year, month, 1)
        self._refresh()

    def _goto_today(self, instance):
        """跳到当前月"""
        self.current_date = date.today()
        self._refresh()

    def _on_date_click(self, btn):
        """
        点了一个日期 → 弹出选择框：白班/晚班/休息/取消
        """
        date_key = btn.date_key
        
        # 弹窗让用户选择班次
        content = BoxLayout(orientation='vertical', spacing=10, padding=10)
        lbl = Label(
            text=f'{date_key} 选择班次',
            font_name='ChineseFont', font_size='16sp'
        )
        content.add_widget(lbl)
        
        # 四个选项按钮
        btn_box = BoxLayout(size_hint_y=0.6, spacing=5)
        for shift_type in ['白班', '晚班', '休息', '取消']:
            b = Button(
                text=shift_type, font_name='ChineseFont', font_size='15sp'
            )
            # 这里用了一个小技巧：把日期和班次类型绑定到按钮上
            b.date_key = date_key
            b.shift_type = shift_type
            b.bind(on_press=self._set_shift)
            btn_box.add_widget(b)
        
        content.add_widget(btn_box)
        
        self.popup = Popup(
            title='设置排班',
            content=content,
            size_hint=(0.7, 0.4),
            auto_dismiss=False  # 点外面不关，必须点按钮
        )
        self.popup.open()

    def _set_shift(self, btn):
        """用户选择了某个班次"""
        date_key = btn.date_key
        shift_type = btn.shift_type
        
        if shift_type == '取消':
            # 删除该天的排班
            if date_key in self.schedule:
                del self.schedule[date_key]
        else:
            # 保存排班
            self.schedule[date_key] = shift_type
        
        self.popup.dismiss()   # 关掉弹窗
        self._refresh()        # 刷新日历（颜色会变）
        self._save_data()      # 保存到文件

    # ────────────── 一键生成闹钟 ──────────────

    def _generate_alarms(self, instance):
        """扫描当月排班，生成闹钟清单并注册"""
        year = self.current_date.year
        month = self.current_date.month
        
        # 收集当月有排班的日期
        day_list = []    # 白班日期列表
        night_list = []  # 晚班日期列表
        rest_list = []   # 休息日期列表
        
        # 清空旧的闹钟，重新注册
        self.alarm_list = []
        self.fired_alarms = set()
        
        for date_key, shift_type in sorted(self.schedule.items()):
            if date_key.startswith(f'{year}-{month:02d}'):
                day = date_key[-2:]
                if shift_type == '白班':
                    day_list.append(day)
                    # 注册白班闹钟
                    alarm_time = f'{date_key} {self.alarm_times["白班"]}'
                    self.alarm_list.append((alarm_time, '白班'))
                elif shift_type == '晚班':
                    night_list.append(day)
                    # 注册晚班闹钟
                    alarm_time = f'{date_key} {self.alarm_times["晚班"]}'
                    self.alarm_list.append((alarm_time, '晚班'))
                elif shift_type == '休息':
                    rest_list.append(day)
        
        # 组装结果显示
        lines = []
        lines.append(f'[ {year}年{month}月 闹钟计划 ]\n')
        lines.append(f'== 白班（{self.alarm_times["白班"]} 响）：')
        if day_list:
            lines.append('    ' + '、'.join(day_list) + '号')
        else:
            lines.append('    （无）')
        lines.append('')
        lines.append(f'== 晚班（{self.alarm_times["晚班"]} 响）：')
        if night_list:
            lines.append('    ' + '、'.join(night_list) + '号')
        else:
            lines.append('    （无）')
        lines.append('')
        lines.append(f'-- 休息：{len(rest_list)} 天')
        lines.append('')
        lines.append(f'共 {len(day_list) + len(night_list)} 个工作日')
        
        result_text = '\n'.join(lines)
        
        # 弹窗显示结果
        content = BoxLayout(orientation='vertical', spacing=10, padding=15)
        lbl = Label(
            text=result_text,
            font_name='ChineseFont',
            font_size='15sp',
            halign='left',
            valign='top',
            text_size=(400, None)  # 限制宽度，让文字自动换行
        )
        content.add_widget(lbl)
        
        btn_ok = Button(
            text='确定',
            font_name='ChineseFont', font_size='16sp',
            size_hint_y=0.25
        )
        btn_ok.bind(on_press=lambda x: self.alarm_popup.dismiss())
        content.add_widget(btn_ok)
        
        self.alarm_popup = Popup(
            title='闹钟计划',
            content=content,
            size_hint=(0.7, 0.6),
            auto_dismiss=False
        )
        self.alarm_popup.open()

    def _check_alarms(self, dt):
        """每30秒执行一次，检查有没有到点的闹钟"""
        now = datetime.now()
        now_str = now.strftime('%Y-%m-%d %H:%M')  # 当前时间，精确到分钟
        
        for alarm_key, shift_type in self.alarm_list:
            # alarm_key 长这样："2026-07-15 07:30"
            alarm_minute = alarm_key[:16]  # 精确到分钟："2026-07-15 07:30"
            
            if now_str == alarm_minute and alarm_key not in self.fired_alarms:
                # 到点了！触发闹钟
                self.fired_alarms.add(alarm_key)
                
                # 弹通知
                self._fire_alarm(alarm_key, shift_type)
    
    def _fire_alarm(self, alarm_key, shift_type):
        """真正触发闹钟：弹系统通知"""
        # 从 "2026-07-15 07:30" 拆出日期和时间
        date_part, time_part = alarm_key.split(' ')
        day = date_part[-2:]  # "15"
        
        # 标记该日期已响过，并在日历上显示✓
        self.fired_dates.add(date_part)
        self._save_data()     # 保存标记，下次打开还在
        
        title = f'[闹钟] {day}号 {shift_type}'
        message = f'{shift_type}闹钟响了！现在是 {time_part}'
        
        # 只在需要时导 plyer（安卓兼容：避免启动时载入 JNI 桥接）
        try:
            from plyer import notification
            notification.notify(
                title=title,
                message=message,
                timeout=10,
            )
        except Exception:
            # 通知失败也没关系，至少打印出来
            print(f'[闹钟] {title} - {message}')

    def _cancel_alarms(self, instance):
        """一键取消所有闹钟"""
        count = len(self.alarm_list)
        self.alarm_list = []
        self.fired_alarms = set()
        
        # 弹个提示
        content = BoxLayout(orientation='vertical', padding=20)
        content.add_widget(Label(
            text=f'已取消 {count} 个闹钟',
            font_name='ChineseFont', font_size='18sp'
        ))
        btn_ok = Button(
            text='确定', font_name='ChineseFont', font_size='16sp',
            size_hint_y=0.3
        )
        btn_ok.bind(on_press=lambda x: popup.dismiss())
        content.add_widget(btn_ok)
        
        popup = Popup(
            title='已取消',
            content=content,
            size_hint=(0.5, 0.3),
            auto_dismiss=False
        )
        popup.open()

    def _clear_schedule(self, instance):
        """清除当月所有排班"""
        year = self.current_date.year
        month = self.current_date.month
        prefix = f'{year}-{month:02d}'
        
        # 找出当月所有排班日期
        to_delete = [k for k in self.schedule if k.startswith(prefix)]
        
        for k in to_delete:
            del self.schedule[k]
        
        self._save_data()
        self._refresh()
        
        # 弹提示
        content = BoxLayout(orientation='vertical', padding=20)
        content.add_widget(Label(
            text=f'已清除当月 {len(to_delete)} 天排班',
            font_name='ChineseFont', font_size='18sp'
        ))
        btn_ok = Button(
            text='确定', font_name='ChineseFont', font_size='16sp',
            size_hint_y=0.3
        )
        btn_ok.bind(on_press=lambda x: popup.dismiss())
        content.add_widget(btn_ok)
        
        popup = Popup(
            title='已清除',
            content=content,
            size_hint=(0.5, 0.3),
            auto_dismiss=False
        )
        popup.open()

    # ────────────── 数据存盘 ──────────────

    def _load_data(self):
        """启动时读取之前保存的数据"""
        if os.path.exists(self.data_file):
            with open(self.data_file, 'r', encoding='utf-8') as f:
                data = json.load(f)        # 把JSON文件读成字典
                # data 大概长这样：
                # {
                #     "schedule": {"2026-07-15": "白班", ...},
                #     "alarm_times": {"白班": "07:30", "晚班": "15:30"}
                # }
                self.schedule = data.get('schedule', {})
                self.alarm_times = data.get('alarm_times', self.alarm_times)
                self.fired_dates = set(data.get('fired_dates', []))

    def _save_data(self):
        """把数据存到JSON文件"""
        data = {
            'schedule': self.schedule,
            'alarm_times': self.alarm_times,
            'fired_dates': list(self.fired_dates),
        }
        with open(self.data_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    # ────────────── 设置闹钟时间 ──────────────

    def _open_settings(self, instance):
        """打开设置弹窗"""
        content = BoxLayout(orientation='vertical', spacing=10, padding=15)
        
        # 生成 00-23 和 00-59 的选项列表
        hours = [f'{h:02d}' for h in range(24)]   # ['00','01',...,'23']
        mins = [f'{m:02d}' for m in range(60)]    # ['00','01',...,'59']
        
        # ── 白班 ──
        content.add_widget(Label(
            text='白班闹钟时间', font_name='ChineseFont', font_size='16sp',
            size_hint_y=0.15
        ))
        row_day = BoxLayout(size_hint_y=0.18, spacing=5)
        
        day_h, day_m = self.alarm_times['白班'].split(':')
        self.sp_day_h = Spinner(
            text=day_h, values=hours, font_name='ChineseFont', font_size='22sp',
            size_hint_x=0.4
        )
        row_day.add_widget(self.sp_day_h)
        
        row_day.add_widget(Label(
            text=':', font_name='ChineseFont', font_size='22sp', bold=True,
            size_hint_x=0.1
        ))
        
        self.sp_day_m = Spinner(
            text=day_m, values=mins, font_name='ChineseFont', font_size='22sp',
            size_hint_x=0.4
        )
        row_day.add_widget(self.sp_day_m)
        
        content.add_widget(row_day)
        
        # ── 晚班 ──
        content.add_widget(Label(
            text='晚班闹钟时间', font_name='ChineseFont', font_size='16sp',
            size_hint_y=0.15
        ))
        row_night = BoxLayout(size_hint_y=0.18, spacing=5)
        
        night_h, night_m = self.alarm_times['晚班'].split(':')
        self.sp_night_h = Spinner(
            text=night_h, values=hours, font_name='ChineseFont', font_size='22sp',
            size_hint_x=0.4
        )
        row_night.add_widget(self.sp_night_h)
        
        row_night.add_widget(Label(
            text=':', font_name='ChineseFont', font_size='22sp', bold=True,
            size_hint_x=0.1
        ))
        
        self.sp_night_m = Spinner(
            text=night_m, values=mins, font_name='ChineseFont', font_size='22sp',
            size_hint_x=0.4
        )
        row_night.add_widget(self.sp_night_m)
        
        content.add_widget(row_night)
        
        # 底部按钮
        btn_box = BoxLayout(size_hint_y=0.2, spacing=10)
        btn_save = Button(
            text='保存', font_name='ChineseFont', font_size='16sp'
        )
        btn_save.bind(on_press=self._save_settings)
        btn_cancel = Button(
            text='取消', font_name='ChineseFont', font_size='16sp'
        )
        btn_cancel.bind(on_press=lambda x: self.settings_popup.dismiss())
        btn_box.add_widget(btn_save)
        btn_box.add_widget(btn_cancel)
        content.add_widget(btn_box)
        
        self.settings_popup = Popup(
            title='闹钟时间设置',
            content=content,
            size_hint=(0.6, 0.5),
            auto_dismiss=False
        )
        self.settings_popup.open()

    def _save_settings(self, instance):
        """保存闹钟设置（从滚轮取值，不用检查格式了）"""
        self.alarm_times['白班'] = f'{self.sp_day_h.text}:{self.sp_day_m.text}'
        self.alarm_times['晚班'] = f'{self.sp_night_h.text}:{self.sp_night_m.text}'
        self._save_data()
        self.settings_popup.dismiss()

    def _check_time(self, t):
        """检查时间格式对不对"""
        if len(t) != 5:
            return False
        if t[2] != ':':
            return False
        try:
            h = int(t[0:2])   # 小时
            m = int(t[3:5])   # 分钟
            return 0 <= h <= 23 and 0 <= m <= 59
        except:
            return False


class ShiftAlarmApp(App):
    """APP入口"""
    def build(self):
        self.title = '排班闹钟'
        # 设置窗口背景色（放 build 里，确保安卓窗口已就绪）
        Window.clearcolor = [0.12, 0.12, 0.15, 1]
        return ShiftCalendar()


if __name__ == '__main__':
    ShiftAlarmApp().run()
