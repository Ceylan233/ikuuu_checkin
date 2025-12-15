# ikuuu机场签到<br/>
## 作用
>每天进行签到，获取额外的流量奖励

## 推送方式
  - 🚀🚀auto_check_in_ikuuu.py脚本采用的是青龙面板，outlook邮箱，163邮箱

# 部署过程
 
1. 右上角Fork此仓库
2. 然后到`Settings`→`Secrets and variables`→`Actions` 新建以下机密：<br/>

  | 参数   | 是否必须  | 内容  | 
  | ------------ | ------------ | ------------ |
  | ACCOUNTS | 是  | 账号密码  |
  | MAIL_USER | 否  | 发件邮箱账号  |
  | MAIL_PASS | 否  | 发件邮箱应用密码(非登陆密码)  |
  | MAIL_TO | 否  | 收件邮箱  |
  
  <b>ACCOUNTS写法：账号:密码(使用冒号:分隔)，有多个账户则配置多行
  
  <b>MAIL_TO：有多个接收通知的账户用逗号‘,’分割
  
  不需要通知可不填写邮箱相关参数

3. 到`Actions`中创建一个workflow，运行一次，以后每天项目都会自动运行。<br/>
4. 最后，可以到Run sign查看签到情况，同时也会也会将签到详情推送。
