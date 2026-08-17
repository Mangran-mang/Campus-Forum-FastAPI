<template>
  <div class="content-enter">
    <h2 style="font-size:20px;margin-bottom:20px">网站公告</h2>

    <div class="announcement-list">
      <!-- 在这里添加新的公告条目，最新的放在最上面 -->
      <!-- 格式：复制一条 .announce-item，修改日期和内容 -->
      <div class="announce-item card">
        <div class="announce-date">2026-08-14</div>
        <h3>论坛业务拓展</h3>
        <p>校园论坛1.0公测版</p>
        <ul>
          <li> 私信功能改为使用websocket实时通讯</li>
          <li> 使退出账号时进行浏览器缓存清理</li>
          <li> 移除了轮询法私信的定时访问</li>
          <li> 完结撒花</li>
        </ul>
        <p>如有问题反馈至3511687086@qq.com</p>
      </div>


      <div class="announce-item card">
        <div class="announce-date">2026-08-14</div>
        <h3>论坛业务拓展</h3>
        <p>校园论坛0.6内测版</p>
        <ul>
          <li> 修复了帖子编辑时间显示bug</li>
          <li> 增加了AI审核员，它会理性删除被举报的帖子</li>
          <li> 修复了用户显示非本人帖子举报按钮为删除按钮的bug</li>
          <li> 尝试解决了浏览器缓存可能会导致账号数据错误的问题</li>
        </ul>
        <p>如有问题反馈至3511687086@qq.com</p>
      </div>

      <div class="announce-item card">
        <div class="announce-date">2026-08-3</div>
        <h3>论坛业务拓展</h3>
        <p>校园论坛0.5内测版</p>
        <ul>
          <li> 修复了邮箱注册的准确性</li>
          <li> 新增了私信功能</li>
          <li> 小站进行了全面装修</li>
          <li> 图片上传功能改为双重验证</li>
          <li> 图片上传后将会被压缩</li>
        </ul>
        <p>如有问题反馈至3511687086@qq.com</p>
      </div>

      <div class="announce-item card">
        <div class="announce-date">2026-07-22</div>
        <h3>论坛业务拓展</h3>
        <p>校园论坛0.43内测版</p>
        <ul>
          <li> 新增举报功能，将直接通知管理员</li>
          <li> 修复了删除帖子功能，现已可以正常使用</li>
        </ul>
        <p>如有问题反馈至3511687086@qq.com</p>
      </div>

      <div class="announce-item card">
        <div class="announce-date">2026-07-15</div>
        <h3>论坛业务拓展</h3>
        <p>校园论坛0.40内测版</p>
        <ul>
          <li>交易模块新增图片功能</li>
          <li>用户可以标记交易情况</li>
          <li>管理员可以删除所有内容了</li>
          <li>修复了迁移链问题</li>
          <li>根据大家的建议新增了等级系统</li>
          <li>增加了等级标识和管理员标识</li>
        </ul>
        <p>如有问题反馈至3511687086@qq.com</p>
      </div>

      <div class="announce-item card">
        <div class="announce-date">2026-07-6</div>
        <h3>论坛业务拓展</h3>
        <p>校园论坛0.30内测版</p>
        <ul>
          <li>新增交易模块</li>
          <li>可以在商品下进行评论了</li>
        </ul>
        <p>如有问题反馈至3511687086@qq.com</p>
      </div>

      <div class="announce-item card">
        <div class="announce-date">2026-06-18</div>
        <h3>论坛正式上线</h3>
        <p>校园论坛0.21内测版</p>
        <ul>
          <li>修复了浏览量显示问题</li>
          <li>修复了通知功能的使用</li>
          <li>增加了论坛通知</li>
          <li>爆金币买了个域名</li>
          <li>炫了个薄荷冰淇淋</li>
        </ul>
        <p>如有问题或建议，欢迎在站内发帖反馈。祝大家使用愉快！</p>
      </div>

      <!-- 添加更多公告：复制上面的 .announce-item 块 -->
    </div>
  </div>
</template>

<script setup>
// 公告内容直接写在 template 里
// 修改后本地 build 再部署即可更新
</script>

<style scoped>
.announcement-list {
  max-width: 700px;
}
.announce-item {
  margin-bottom: 16px;
}
.announce-item:last-child {
  margin-bottom: 0;
}
.announce-date {
  font-size: 12px;
  color: var(--text-muted);
  margin-bottom: 6px;
}
.announce-item h3 {
  font-size: 16px;
  margin-bottom: 8px;
  color: var(--primary);
}
.announce-item p {
  font-size: 14px;
  line-height: 1.7;
  color: var(--text-secondary);
  margin-bottom: 6px;
}
.announce-item ul {
  margin: 6px 0 10px 20px;
  font-size: 14px;
  color: var(--text-secondary);
  line-height: 1.8;
}
.announce-item ul li {
  margin-bottom: 2px;
}

@media (max-width: 768px) {
  .announce-item h3 {
    font-size: 15px;
  }
  .announce-item p,
  .announce-item ul {
    font-size: 13px;
  }
}
</style>
