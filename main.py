# -*- coding: utf-8 -*-
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.chrome.service import Service
import yaml
import time
import logging
import random
import threading
from queue import Queue
from concurrent.futures import ThreadPoolExecutor
import requests
import json
import undetected_chromedriver as uc
from fake_useragent import UserAgent


# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('automation.log'),
        logging.StreamHandler()
    ]
)

class BrowserManager:
    def __init__(self, config):
        self.config = config
        self.drivers = []
        self.ads_api_url = config.get('ads_api_url', "http://127.0.0.1:50325/api/v1/browser/local-active")
        self.browser_accounts = config.get('browser_accounts', {})
        self.task_type = config.get('task_types', [])
        self.task_config = config.get('task_config', {})
        
    def get_active_browsers(self):
        """通过ADS API获取已启动的浏览器列表"""
        try:
            response = requests.get(self.ads_api_url)
            if response.status_code == 200:
                data = response.json()
                if data.get('code') == 0:
                    return data.get('data', {}).get('list', [])
                else:
                    logging.error(f"API request failed: {data.get('msg')}")
            else:
                logging.error(f"HTTP request failed with status code: {response.status_code}")
        except Exception as e:
            logging.error(f"Failed to get active browsers: {str(e)}")
        return []

    def connect_to_browser(self, browser_info):
        """连接到指定的浏览器窗口"""
        try:
            user_id = browser_info.get('user_id')
            if not user_id:
                logging.error(f"No user_id found for browser: {browser_info}")
                return None
                
            # 获取浏览器对应的账号配置
            account_config = self.browser_accounts.get(user_id)
            if not account_config:
                logging.error(f"No account configuration found for browser_id: {user_id}")
                return None
            
            selenium_address = browser_info.get('ws', {}).get('selenium')
            webdriver_path = browser_info.get('webdriver')
          
            if not selenium_address:
                logging.error(f"No selenium address found for browser: {browser_info}")
                return None
            
            # 连接到Chrome
            options = webdriver.ChromeOptions()
            options.add_experimental_option("debuggerAddress", selenium_address)
            
            # 如果提供了webdriver路径，使用它
            if webdriver_path:
                service = Service(executable_path=webdriver_path)
                driver = webdriver.Chrome(service=service, options=options)
            else:
                driver = webdriver.Chrome(options=options)
            
            # 验证连接
            driver.current_url
            
            # 将账号配置附加到driver对象
            driver.account_config = account_config
            
            return driver
            
        except Exception as e:
            logging.error(f"Failed to connect to browser: {str(e)}")
            return None

    def initialize_browsers(self):
        """连接到所有已存在的ADS指纹浏览器窗口"""
        # 获取已启动的浏览器列表
        active_browsers = self.get_active_browsers()
        logging.info(f"Found {len(active_browsers)} active browser windows")
        
        # 连接到每个窗口
        for browser in active_browsers:
            driver = self.connect_to_browser(browser)
            if driver:
                self.drivers.append(driver)
                logging.info(f"Successfully connected to browser with debug port: {browser.get('debug_port')}")
            else:
                logging.error(f"Failed to connect to browser with debug port: {browser.get('debug_port')}")

    def close_all(self):
        """关闭所有浏览器连接"""
        for driver in self.drivers:
            try:
                driver.quit()
            except:
                pass

class TaskAutomation:
    def __init__(self, config_path='config.yaml'):
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)
        
        self.browser_manager = BrowserManager(self.config)
        self.task_queue = Queue()
        self.results = []
        self.lock = threading.Lock()

    def login_task_site(self, driver):
        """登录任务平台"""
        logging.info(f"Logging into task platform with driver {id(driver)}")
        #driver.get()

        # # 打开一个新标签页
        # driver.execute_script("window.open('about:blank', '_blank')")

        # # 切换到新标签页
        # driver.switch_to.window(driver.window_handles[1])

        task_site_url = self.config['task_site_url']
        logging.info(f"url is {task_site_url}")
        # 在新标签页中打开URL
        driver.get(self.config['task_site_url'])
        
        # try:
        #     # 获取该浏览器对应的账号配置
        #     account_config = driver.account_config['task_site_account']
            
        #     # 等待登录表单加载
        #     username_field = WebDriverWait(driver, 20).until(
        #         EC.presence_of_element_located((By.ID, 'username')))
            
        #     # 随机延迟输入
        #     for char in account_config['username']:
        #         username_field.send_keys(char)
        #         time.sleep(random.uniform(0.1, 0.3))
            
        #     password_field = driver.find_element(By.ID, 'password')
        #     for char in account_config['password']:
        #         password_field.send_keys(char)
        #         time.sleep(random.uniform(0.1, 0.3))
            
        #     # 点击登录按钮
        #     submit_btn = driver.find_element(By.XPATH, '//button[@type="submit"]')
        #     submit_btn.click()
            
             # 等待登录成功
        time.sleep(random.uniform(2, 4))
            
        return True
        # except Exception as e:
        #     logging.error(f"Login failed: {str(e)}")
        #     return False

    def handle_twitter_actions(self, driver, task_type):
        """处理Twitter相关操作"""
        tw = TwitterHandler(driver)
        try:
            # 获取该浏览器对应的Twitter账号配置
            twitter_account = driver.account_config['twitter_account']
            
            if task_type == 'retweet':
                success = tw.retweet_post()
            elif task_type == 'like':
                success = tw.like_post()
            elif task_type == 'comment':
                success = tw.add_comment(random.choice(self.config['comments_pool']))
            else:
                success = False
                
            return success
        except Exception as e:
            logging.error(f"Twitter action failed: {str(e)}")
            return False

    def process_single_task(self, driver, task_type):
        """处理单个任务"""
        try:

            logging.info(f"Processing task: {task_type}")
            taskConfig = self.task_config.get(task_type)
            # 点击任务按钮
            task_button = self.wait.until(EC.element_to_be_clickable(
                        (By.XPATH, taskConfig[0])))
            original_window = driver.current_window_handle
            task_button.click()# 等待倒计时开始
            # try:
            #     countdown_element = WebDriverWait(driver, 10).until(
            #         EC.presence_of_element_located((By.XPATH, '//div[contains(text(), "60")]'))
            #     )
            #     logging.info("Countdown started")
            # except TimeoutException:
            #     logging.error("Countdown not found")
            #     return False
            
            # 
            
            # 等待倒计时结束
            time.sleep(65)  # 等待倒计时结束
            
            # 循环尝试验证，直到任务完成
            max_attempts = 5
            attempt = 0
            while attempt < max_attempts:
                try:
                    # 查找验证按钮
                    verify_button = WebDriverWait(driver, 10).until(
                        EC.element_to_be_clickable((By.XPATH, taskConfig[1]))
                    )
                    
                    # 点击验证按钮
                    verify_button.click()
                    logging.info(f"Clicked verify button, attempt {attempt + 1}")
                    
                    # 等待任务按钮消失或倒计时重新开始
                    try:
                        task_button = WebDriverWait(driver, 10).until(
                            EC.element_to_be_clickable((By.XPATH, taskConfig[0]))
                        )
                        WebDriverWait(driver, 10).until(
                            EC.invisibility_of_element(task_button)
                        )
                        logging.info("Task completed successfully")
                        return True
                    except TimeoutException:
                        # 如果倒计时重新开始，等待它结束
                        try:
                            # countdown_element = WebDriverWait(driver, 10).until(
                            #     EC.presence_of_element_located((By.XPATH, '//div[contains(text(), "60")]'))
                            # )
                            logging.info("Countdown restarted, waiting...")
                            time.sleep(65)
                        except TimeoutException:
                            # 如果倒计时没有重新开始，可能任务已经完成
                            logging.info("Task might be completed")
                            return True
                    
                except TimeoutException:
                    logging.error(f"Verify button not found on attempt {attempt + 1}")
                    return False
                
                attempt += 1
            
            logging.error("Max verification attempts reached")
            return False
            
        except Exception as e:
            logging.error(f"Task processing failed: {str(e)}")
            return False

    def process_tasks_with_multiple_windows(self, num_windows=15):
        """使用多个窗口处理任务"""
        # 初始化浏览器
        #self.browser_manager.initialize_browsers()
        
        try:
            # 为每个窗口创建任务处理线程
            with ThreadPoolExecutor(max_workers=num_windows) as executor:
                futures = []
                for driver in self.browser_manager.drivers:
                    future = executor.submit(self.process_window_tasks, driver)
                    futures.append(future)
                
                # 等待所有任务完成
                for future in futures:
                    future.result()
                    
        finally:
            self.browser_manager.close_all()

    def process_window_tasks(self, driver):
        """处理单个窗口的任务"""
        try:
            # 登录
            if not self.login_task_site(driver):
                return
            for task_type in self.task_type:
                try:
                    # 检查任务是否已完成
                    taskConfig = self.task_config.get(task_type)
                    taskbtn = self.wait.until(EC.element_to_be_clickable(
                        (By.XPATH, taskConfig[0])))
                    if not taskbtn:
                        logging.info("Task already completed, skipping...")
                    else:    
                        success = self.process_single_task(driver, task_type)
                        with self.lock:
                            self.results.append({
                                'task': task_type,
                                'success': success
                            })
                except Exception as e:
                    logging.error(f"Error processing task: {str(e)}")
                
                    
        except Exception as e:
            logging.error(f"Window task processing failed: {str(e)}")

    def identify_task_type(self, task_title):
        """识别任务类型"""
        task_title = task_title.lower()
        if 'watch' in task_title or '观看' in task_title:
            return 'watch'
        elif 'share' in task_title or '分享' in task_title:
            return 'share'
        elif 'quote' in task_title or '引用' in task_title:
            return 'quote'
        elif 'reply' in task_title or '回复' in task_title:
            return 'reply'
        elif 'like' in task_title or '点赞' in task_title:
            return 'like'
        return 'unknown'

    def handle_website_visit(self, driver):
        """处理网站访问任务"""
        try:
            # 随机等待时间模拟真实访问
            time.sleep(random.uniform(3, 7))
            return True
        except Exception as e:
            logging.error(f"Website visit failed: {str(e)}")
            return False

    def complete_task(self, driver, task_element):
        """标记任务完成"""
        try:
            complete_btn = task_element.find_element(
                By.XPATH, './/button[contains(text(),"Verify")]')
            complete_btn.click()
            WebDriverWait(driver, 20).until(
                EC.invisibility_of_element(complete_btn))
            logging.info("Task marked as completed")
            return True
        except Exception as e:
            logging.error(f"Failed to complete task: {str(e)}")
            return False

class TwitterHandler:
    def __init__(self, driver):
        self.driver = driver
        self.wait = WebDriverWait(driver, 20)
        self.twitter_account = driver.account_config['twitter_account']

    def login_twitter(self):
        """登录Twitter账号"""
        try:
            self.driver.get("https://twitter.com/login")
            time.sleep(random.uniform(2, 4))
            
            # 输入用户名
            username_field = self.wait.until(EC.presence_of_element_located(
                (By.XPATH, '//input[@autocomplete="username"]')))
            for char in self.twitter_account['username']:
                username_field.send_keys(char)
                time.sleep(random.uniform(0.1, 0.3))
            
            # 点击下一步
            next_btn = self.wait.until(EC.element_to_be_clickable(
                (By.XPATH, '//span[text()="Next"]')))
            next_btn.click()
            time.sleep(random.uniform(1, 2))
            
            # 输入密码
            password_field = self.wait.until(EC.presence_of_element_located(
                (By.XPATH, '//input[@name="password"]')))
            for char in self.twitter_account['password']:
                password_field.send_keys(char)
                time.sleep(random.uniform(0.1, 0.3))
            
            # 点击登录
            login_btn = self.wait.until(EC.element_to_be_clickable(
                (By.XPATH, '//span[text()="Log in"]')))
            login_btn.click()
            
            # 等待登录成功
            time.sleep(random.uniform(3, 5))
            return True
            
        except Exception as e:
            logging.error(f"Twitter login failed: {str(e)}")
            return False

    def retweet_post(self):
        """执行转推操作"""
        try:
            # 等待并点击转推按钮
            retweet_btn = self.wait.until(EC.element_to_be_clickable(
                (By.XPATH, '//div[@data-testid="retweet"]')))
            retweet_btn.click()
            
            # 随机延迟
            time.sleep(random.uniform(1, 2))
            
            # 确认转推
            confirm_btn = self.wait.until(EC.element_to_be_clickable(
                (By.XPATH, '//div[@data-testid="retweetConfirm"]')))
            confirm_btn.click()
            
            # 等待转推完成
            time.sleep(random.uniform(2, 3))
            return True
        except Exception as e:
            logging.error(f"Retweet failed: {str(e)}")
            return False
    
    def like_post(self):
        """执行点赞操作"""
        try:
            like_btn = self.wait.until(EC.element_to_be_clickable(
                (By.XPATH, '//div[@data-testid="like"]')))
            like_btn.click()
            time.sleep(random.uniform(1, 2))
            return True
        except Exception as e:
            logging.error(f"Like failed: {str(e)}")
            return False
    
    def add_comment(self, comment):
        """执行评论操作"""
        try:
            # 点击评论按钮
            comment_btn = self.wait.until(EC.element_to_be_clickable(
                (By.XPATH, '//div[@data-testid="reply"]')))
            comment_btn.click()
            
            # 输入评论
            comment_field = self.wait.until(EC.presence_of_element_located(
                (By.XPATH, '//div[@data-testid="tweetTextarea_0"]')))
            
            # 模拟人工输入
            for char in comment:
                comment_field.send_keys(char)
                time.sleep(random.uniform(0.1, 0.3))
            
            # 发送评论
            reply_btn = self.wait.until(EC.element_to_be_clickable(
                (By.XPATH, '//div[@data-testid="tweetButton"]')))
            reply_btn.click()
            
            time.sleep(random.uniform(2, 3))
            return True
        except Exception as e:
            logging.error(f"Comment failed: {str(e)}")
            return False

if __name__ == "__main__":
    try:
        bot = TaskAutomation()
        # 连接到已存在的浏览器窗口
        bot.browser_manager.initialize_browsers()
        
        if not bot.browser_manager.drivers:
            logging.error("No browser windows found to connect to")
            exit(1)
            
        # 处理任务
        bot.process_tasks_with_multiple_windows(len(bot.browser_manager.drivers))
        
        # 输出结果统计
        success_count = sum(1 for r in bot.results if r['success'])
        total_count = len(bot.results)
        logging.info(f"Task completion summary: {success_count}/{total_count} tasks completed successfully")
        
    except Exception as e:
        logging.error(f"Fatal error: {str(e)}")
    finally:
        if hasattr(bot, 'browser_manager'):
            bot.browser_manager.close_all()