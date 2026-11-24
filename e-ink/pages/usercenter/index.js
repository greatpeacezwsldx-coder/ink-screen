import { fetchUserCenter } from '../../services/usercenter/fetchUsercenter';
import Toast from 'tdesign-miniprogram/toast/index';

const menuData = [
  {
    title: '相册管理',
    icon: 'image',
    type: 'album',
  },
  {
    title: '设备连接',
    icon: 'bluetooth',
    type: 'device',
  },
  {
    title: 'AI设置',
    icon: 'lightbulb',
    type: 'ai',
  },
  {
    title: '关于设备',
    icon: 'info-circle',
    type: 'about',
  },
];

const getDefaultData = () => ({
  userInfo: {
    avatarUrl: '',
    nickName: '正在登录...',
    phoneNumber: '',
  },
  menuData,
  currAuthStep: 1,
  versionNo: '',
});

Page({
  data: getDefaultData(),

  onLoad() {
    this.getVersionInfo();
  },

  onShow() {
    this.getTabBar().init();
    this.init();
  },
  onPullDownRefresh() {
    this.init();
  },

  init() {
    this.fetUseriInfoHandle();
  },

  fetUseriInfoHandle() {
    fetchUserCenter().then(({ userInfo }) => {
      this.setData({
        userInfo,
        currAuthStep: 2,
      });
      wx.stopPullDownRefresh();
    });
  },

  onClickCell({ currentTarget }) {
    const { type } = currentTarget.dataset;
    const messages = {
      album: '相册管理',
      device: '设备连接',
      ai: 'AI设置',
      about: '关于设备',
    };
    Toast({
      context: this,
      selector: '#t-toast',
      message: `你点击了${messages[type]}`,
      icon: '',
      duration: 1000,
    });
  },

  gotoUserEditPage() {
    const { currAuthStep } = this.data;
    if (currAuthStep === 2) {
      wx.navigateTo({ url: '/pages/user/person-info/index' });
    } else {
      this.fetUseriInfoHandle();
    }
  },

  getVersionInfo() {
    const versionInfo = wx.getAccountInfoSync();
    const { version, envVersion = __wxConfig } = versionInfo.miniProgram;
    this.setData({
      versionNo: envVersion === 'release' ? version : envVersion,
    });
  },
});
