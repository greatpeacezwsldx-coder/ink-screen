// ThisDayBefore.ets - 往年今日页面
import router from '@ohos.router';
import http from '@ohos.net.http';
import { promptAction } from '@kit.ArkUI';

interface PhotoItem {
  name: string;
  url: string;
  date: string;
  monthDay: string;
}

@Entry
@Component
struct ThisDayBefore {
  @State photoList: PhotoItem[] = [];
  @State filteredPhotos: PhotoItem[] = [];
  @State isLoading: boolean = false;
  @State todayMonthDay: string = '';

  private readonly OBS_BASE_URL: string = 'https://mypublicbucket0101.obs.cn-north-4.myhuaweicloud.com/small/';
  private readonly NAME_FILE_URL: string = 'https://mypublicbucket0101.obs.cn-north-4.myhuaweicloud.com/small/name.txt';

  aboutToAppear(): void {
    const today: Date = new Date();
    const month: string = String(today.getMonth() + 1).padStart(2, '0');
    const day: string = String(today.getDate()).padStart(2, '0');
    this.todayMonthDay = `${month}-${day}`;
    this.fetchPhotoList();
  }

  async fetchPhotoList(): Promise<void> {
    this.isLoading = true;
    try {
      const httpClient = http.createHttp();
      const result = await httpClient.request(this.NAME_FILE_URL, {
        method: http.RequestMethod.GET,
        connectTimeout: 30000,
        readTimeout: 30000
      });

      if (result.responseCode === 200) {
        const content: string = result.result as string;
        const lines: string[] = content.split('\n');
        const fileNames: string[] = [];

        for (let i = 0; i < lines.length; i++) {
          const name: string = lines[i].trim();
          if (name.length > 0 && (name.endsWith('.jpg') || name.endsWith('.png') || name.endsWith('.jpeg'))) {
            fileNames.push(name);
          }
        }

        const tempList: PhotoItem[] = [];
        for (let i = 0; i < fileNames.length; i++) {
          const name: string = fileNames[i];
          const dateStr: string = this.extractDateFromName(name);
          const monthDay: string = this.extractMonthDay(dateStr);
          tempList.push({
            name: name,
            url: this.OBS_BASE_URL + encodeURIComponent(name),
            date: dateStr,
            monthDay: monthDay
          });
        }
        this.photoList = tempList;

        this.filterByMonthDay();
      } else {
        promptAction.showToast({ message: '加载失败，请重试', duration: 2000 });
      }
      httpClient.destroy();
    } catch (err) {
      console.error('获取照片列表失败:', JSON.stringify(err));
      promptAction.showToast({ message: '网络错误，请检查网络连接', duration: 2000 });
    } finally {
      this.isLoading = false;
    }
  }

  private extractDateFromName(name: string): string {
    const match = name.match(/\d{4}[-_]?\d{2}[-_]?\d{2}/);
    if (match) {
      const dateStr: string = match[0].replace(/[_-]/g, '');
      if (dateStr.length === 8) {
        return `${dateStr.substring(0, 4)}-${dateStr.substring(4, 6)}-${dateStr.substring(6, 8)}`;
      }
    }
    const dateMatch = name.match(/(\d{4})(\d{2})(\d{2})/);
    if (dateMatch) {
      return `${dateMatch[1]}-${dateMatch[2]}-${dateMatch[3]}`;
    }
    return '未知日期';
  }

  private extractMonthDay(dateStr: string): string {
    if (dateStr === '未知日期') {
      return '未知';
    }
    const parts: string[] = dateStr.split('-');
    if (parts.length === 3) {
      return `${parts[1]}-${parts[2]}`;
    }
    return '未知';
  }

  filterByMonthDay(): void {
    const tempList: PhotoItem[] = [];
    for (let i = 0; i < this.photoList.length; i++) {
      if (this.photoList[i].monthDay === this.todayMonthDay) {
        tempList.push(this.photoList[i]);
      }
    }
    this.filteredPhotos = tempList;
  }

  build() {
    Column() {
      Row() {
        Image($r('sys.symbol.arrow_left'))
          .width(24)
          .height(24)
          .onClick(() => router.back())
        Text('往年今日')
          .fontSize(20)
          .fontWeight(FontWeight.Bold)
          .margin({ left: 16 })
        Blank()
      }
      .width('100%')
      .height(56)
      .padding({ left: 16, right: 16 })
      .backgroundColor(Color.White)

      Row() {
        Text(`显示 ${this.todayMonthDay} 的照片`)
          .fontSize(16)
          .fontColor('#333333')
      }
      .width('100%')
      .padding({ left: 16, top: 16, bottom: 8 })

      Row() {
        Text(`共 ${this.filteredPhotos.length} 张照片`)
          .fontSize(14)
          .fontColor('#666666')
      }
      .width('100%')
      .padding({ left: 16, bottom: 16 })

      if (this.isLoading) {
        Column() {
          LoadingProgress()
            .width(50)
            .height(50)
          Text('加载中...')
            .fontSize(14)
            .fontColor('#999999')
            .margin({ top: 16 })
        }
        .width('100%')
        .height('60%')
        .justifyContent(FlexAlign.Center)
      } else if (this.filteredPhotos.length === 0) {
        Column() {
          Text('📷')
            .fontSize(60)
            .fontColor('#CCCCCC')
          Text(`暂无 ${this.todayMonthDay} 的照片`)
            .fontSize(16)
            .fontColor('#999999')
            .margin({ top: 16 })
        }
        .width('100%')
        .height('60%')
        .justifyContent(FlexAlign.Center)
      } else {
        Scroll() {
          Grid() {
            ForEach(this.filteredPhotos, (photo: PhotoItem) => {
              GridItem() {
                Column() {
                  Image(photo.url)
                    .width('100%')
                    .aspectRatio(1)
                    .borderRadius(8)
                    .objectFit(ImageFit.Cover)
                    .backgroundColor('#F0F0F0')
                  Text(photo.date)
                    .fontSize(12)
                    .fontColor('#666666')
                    .margin({ top: 4 })
                }
              }
              .padding(4)
            })
          }
          .columnsTemplate('1fr 1fr 1fr')
          .columnsGap(8)
          .rowsGap(8)
          .padding({ left: 12, right: 12 })
        }
        .width('100%')
        .layoutWeight(1)
        .scrollBar(BarState.Auto)
      }
    }
    .width('100%')
    .height('100%')
    .backgroundColor('#FAFAFA')
  }
}
